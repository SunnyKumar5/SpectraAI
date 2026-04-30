# SpectraAI — System Architecture

## High-Level Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                        SpectraAI Desktop App                       │
├──────────┬────────────────────────────┬───────────────────────────┤
│  INPUT   │         CENTER             │       VALIDATION          │
│  PANEL   │  Spectrum + Interpretation │   Gauge + Radar + Table   │
└──────────┴────────────────────────────┴───────────────────────────┘
       │                  │                        │
       ▼                  ▼                        ▼
┌──────────┐    ┌─────────────────┐    ┌───────────────────┐
│ Parsers  │───>│   AI Engine     │───>│ Validation Engine │
│          │    │ (Claude/Gemini) │    │  (Rule-based)     │
└──────────┘    └─────────────────┘    └───────────────────┘
       │                  │                        │
       ▼                  ▼                        ▼
┌──────────────────────────────────────────────────────────┐
│                    Core Data Models                       │
│  Molecule │ NMRData │ IRData │ MSData │ ValidationReport │
└──────────────────────────────────────────────────────────┘
```

## Module Architecture

### 1. Core Data Models (`core/`)

Immutable data layer — no business logic, pure data + serialization.

```
Molecule ─┬─ MoleculeMetadata (scaffold_family, reaction_type, catalyst)
          ├─ h1_nmr: NMRData ── NMRPeak[] (shift, multiplicity, J, assignment)
          ├─ c13_nmr: NMRData
          ├─ ir: IRData ── IRAbsorption[] (wavenumber, intensity, assignment)
          ├─ hrms: MSData (technique, ion_type, calc/obs mz, ppm_error)
          └─ uv: UVData ── UVAbsorption[] (wavelength, extinction_coeff)
```

Key design decisions:
- All models are `@dataclass` with `to_dict()` / `from_dict()` roundtrip
- AI-related fields (ai_assignment, ai_confidence, ai_status) live on peaks
- `Molecule.data_completeness` tracks coverage across all 8 data types
- Formula parsing handles both Hill notation and subscript Unicode

### 2. Parsers (`parsers/`)

Convert journal-style text into structured core models.

```
"¹H NMR (400 MHz, CDCl₃): δ 8.15 (d, J = 6.8 Hz, 1H)"
                    │
            NMRTextParser.parse_h1()
                    │
                    ▼
NMRData(nucleus="1H", frequency=400, solvent="CDCl3",
        peaks=[NMRPeak(shift=8.15, mult="d", J=[6.8], integ=1.0)])
```

Parser strategy:
- Regex-based extraction with Unicode normalization
- Fallback parsing when detailed patterns fail
- JCAMP-DX support for instrument output files
- CSV batch import for multi-compound datasets

### 3. AI Engine (`ai/`)

Unified LLM interface with domain-expert prompt templates.

```
LLMClient (provider-agnostic)
    ├── generate(system, user) → text
    ├── generate_json(system, user) → dict
    └── generate_stream(system, user) → Generator[str]

NMRInterpreter
    ├── interpret_h1(data, smiles, formula, scaffold) → dict
    └── interpret_c13(data, smiles, formula, scaffold) → dict

IRInterpreter
    └── interpret(data, smiles, formula) → dict

CrossSpectralAnalyzer
    └── analyze(mol, h1, c13, ir, ms) → str

CharacterizationWriter
    └── generate(mol, h1, c13, ir, ms) → str
```

Prompt design principles:
1. **Domain expert persona** — "Senior organic chemist, 25+ years heterocycle specialization"
2. **Scaffold context injection** — Reference NMR ranges prepended when scaffold is known
3. **Structured JSON output** — Consistent `peaks[]` array with confidence scores
4. **Cross-spectral reasoning** — Multi-step chain-of-thought across data types
5. **Error awareness** — Prompts include common pitfalls (solvent peaks, impurities)

### 4. Validation Engine (`validation/`)

Rule-based checks producing weighted scores.

```
ValidationEngine
    ├── CarbonCountChecker   (15% weight)  ── ¹³C peaks vs formula carbon count
    ├── ProtonCountChecker   (15% weight)  ── ¹H integration vs formula H count
    ├── FunctionalGroupChecker (15% weight) ── IR bands vs SMILES substructures
    ├── MSFormulaChecker     (20% weight)  ── ppm error + ion formula match
    ├── SymmetryChecker      (10% weight)  ── Equivalent protons/carbons
    ├── IRStructureChecker   (10% weight)  ── Expected IR bands from structure
    └── CrossSpectralChecker (15% weight)  ── Consistency across all data
```

Each checker returns: `ValidationCheck(status, score, expected, observed, explanation)`

### 5. UI System (`ui/`)

PyQt5 with signal-based inter-panel communication.

```
MainWindow
    ├── InputPanel          ──signal──> analyze_requested
    ├── SpectrumPanel       <──slot──── plot_h1_nmr / plot_ir
    ├── InterpretationPanel <──slot──── set_interpretation / set_peaks
    └── ValidationPanel     <──slot──── set_report
```

Custom widgets:
- **ConfidenceGauge** — Animated arc gauge (0–100)
- **RadarChart** — Per-category polygon overlay
- **CompletenessRing** — Data coverage donut chart
- **AnimatedText** — Typewriter-effect text display
- **SplashScreen** — Branded loading screen

### 6. Prediction Module (`prediction/`)

Structure prediction from spectral data (Phase 2+).

```
ScaffoldEnumerator → generate candidates from scaffold family
CandidateRanker   → score candidates against spectral evidence
NMRPredictor      → predict expected shifts for candidate structures
```

---

## Analysis Pipeline Sequence

```
1. User clicks "Analyze"
2. InputPanel → MainWindow._run_analysis()
3. Parse text inputs → NMRData, IRData, MSData
4. Plot spectra immediately (SpectrumPanel)
5. Launch AnalysisWorker (QThread):
   a. NMRInterpreter.interpret_h1()  → emit h1_result
   b. NMRInterpreter.interpret_c13() → emit c13_result
   c. IRInterpreter.interpret()      → emit ir_result
   d. MSValidator.validate()         → emit ms_result
   e. CrossSpectralAnalyzer.analyze()→ emit cross_result
   f. ValidationEngine.validate()    → emit validation_done
   g. CharacterizationWriter.generate() → emit char_result
6. Each signal updates the corresponding panel
7. finished_all signal hides progress bar
```

---

## Supported Scaffold Families

| Scaffold | ¹H Refs | ¹³C Refs | Diagnostic Features |
|----------|---------|----------|---------------------|
| Imidazo[1,2-a]pyridine | H-3, H-5, H-6, H-7, H-8 | C-2, C-3, C-5, C-8a | H-3 singlet 7.4–8.6 ppm |
| Indole | N-H, H-2, H-3, H-4–H-7 | C-2, C-3, C-3a, C-7a | N-H broad singlet 7.8–10.5 |
| Quinazoline | H-2, H-5, H-6, H-7, H-8 | C-2, C-4, C-4a, C-8a | H-2 singlet 8.8–9.5 |
| 1,2,3-Triazole | H-5 | C-4, C-5 | H-5 singlet 7.4–8.5 |
| Pyrazolo[1,5-a]pyrimidine | H-3, H-5, H-6 | C-3, C-5, C-7 | H-3 singlet 6.5–7.5 |
| Coumarin | H-3, H-4, H-5–H-8 | C-2, C-3, C-4, C-9a | Lactone C=O at 160–165 |
