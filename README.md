<<<<<<< HEAD
# SpectraAI — Multi-Spectral Generative AI Suite

**Scaffold-Constrained Multi-Spectral Analysis for Heterocycle Characterization**

A professional PyQt5 desktop application combining generative AI (Claude / Gemini) with multi-spectral reasoning (¹H NMR, ¹³C NMR, IR, HRMS, UV-Vis) to interpret, validate, and predict molecular structures — specialized for synthetic heterocycles.

---

## Research Novelty

SpectraAI introduces **six key innovations** not found in existing tools:

1. **Multi-Spectral AI Reasoning** — Cross-validates ¹H NMR, ¹³C NMR, IR, and HRMS simultaneously with chain-of-thought analysis
2. **Scaffold-Constrained Interpretation** — Injects NMR reference ranges for specific heterocyclic families (imidazopyridines, indoles, quinazolines, triazoles, etc.) to guide AI reasoning
3. **Hybrid Validation** — Combines rule-based checks (carbon count, proton count, mass accuracy) with AI assessment for confidence scoring
4. **Ionic Liquid Awareness** — Accounts for NMR chemical shift perturbations in ionic liquid reaction media
5. **Automated Characterization Text** — Generates publication-ready compound characterization paragraphs
6. **Error Detection Benchmarking** — Deliberately introduces spectral errors to measure AI diagnostic accuracy

---

## Features

### Core Analysis
- ¹H NMR peak-by-peak interpretation with coupling pattern analysis
- ¹³C NMR carbon assignment with DEPT correlation
- IR functional group identification and consistency checking
- HRMS mass accuracy validation (ppm error calculation)
- Cross-spectral consistency analysis across all data types
- Automated publication-ready characterization text generation

### Validation Dashboard
- Confidence gauge (animated 0–100 score)
- Radar chart showing per-category scores
- Individual check results table with color-coded status
- Natural language validation summary

### Visualization
- Interactive NMR stick plots with Lorentzian line shapes
- IR spectrum display with functional group region labeling
- Completeness ring showing data coverage

### Scaffold Support
- Imidazo[1,2-a]pyridines
- Indoles
- Quinazolines / Quinazolinones
- 1,2,3-Triazoles
- Pyrazolo[1,5-a]pyrimidines
- Coumarins
- Extensible to new scaffolds

---

## Installation

### Prerequisites
- Python 3.10 or higher
- API key for Claude (Anthropic) or Gemini (Google)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/spectra-ai.git
cd spectra-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Install RDKit for 2D structure rendering
pip install rdkit-pypi

# Configure API key
cp .env.example .env
# Edit .env and add your API key

# Run the application
python run.py
```

### Environment Variables

Set your API key before running:

```bash
# For Claude (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# For Gemini
export GOOGLE_API_KEY="AI..."
```

Or configure via the Settings dialog (Ctrl+,) in the application.

---

## Usage

### Basic Workflow

1. **Enter compound data** — SMILES, molecular formula, scaffold family
2. **Paste spectral data** — ¹H NMR, ¹³C NMR, IR, HRMS from your experimental section
3. **Click Analyze** (or Ctrl+Enter) — AI interprets all spectra simultaneously
4. **Review results** — Interpretation, validation checks, confidence score
5. **Generate text** — Copy publication-ready characterization to manuscript
6. **Export** — Save as JSON or PDF report

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Run analysis |
| `Ctrl+O` | Open compound file |
| `Ctrl+S` | Save compound file |
| `Ctrl+E` | Export PDF report |
| `Ctrl+,` | Open settings |
| `Ctrl+Shift+C` | Clear all data |
| `Escape` | Cancel running analysis |

### Sample Data

Three sample compounds are included for testing:

- `SPEC-001` — 3-(4-Methoxyphenyl)imidazo[1,2-a]pyridine
- `SPEC-002` — 2-Phenyl-1H-indole
- `SPEC-003` — 1-Benzyl-4-phenyl-1H-1,2,3-triazole

Load via File → Open Compound JSON.

---

## Architecture

```
SpectraAI/
├── src/spectra_ai/
│   ├── core/           # Data models (Molecule, NMRData, IRData, MSData, etc.)
│   ├── parsers/        # Text parsers (NMR, IR, MS from experimental sections)
│   ├── ai/             # LLM client + interpreters + prompt templates
│   │   └── prompts/    # Domain-expert prompt templates (10 specialized prompts)
│   ├── validation/     # Rule-based validation engine (7 checker modules)
│   ├── ui/             # PyQt5 panels (Input, Spectrum, Interpretation, Validation)
│   │   ├── widgets/    # Custom widgets (gauge, radar, ring, animated text)
│   │   └── styles/     # Dark theme + color palette
│   ├── utils/          # Reference data (NMR ranges, IR bands, SMILES utils)
│   └── data/           # Sample compounds + scaffold references
├── tests/              # Comprehensive test suite
├── run.py              # Quick launch script
└── pyproject.toml      # Project configuration
```

### Data Flow

```
User Input → Parsers → Core Models → AI Engine (LLM) → Interpretation
                                    → Validation Engine → Report
                                    → Text Generator → Characterization
```

### AI Prompt Strategy

SpectraAI uses five principles for effective chemical AI reasoning:

1. **Domain Expert Persona** — Senior organic chemist with heterocycle specialization
2. **Scaffold Context Injection** — Reference NMR ranges injected before interpretation
3. **Structured JSON Output** — Consistent parsing of AI results
4. **Cross-Spectral Chain-of-Thought** — Multi-step reasoning across data types
5. **Error Injection Testing** — Benchmarkable error detection accuracy

---

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=spectra_ai --cov-report=html
```

### Project Structure Conventions

- All data models use Python dataclasses with JSON serialization
- AI responses are always structured JSON (parsed from LLM output)
- Validation checks follow a standard interface (BaseChecker)
- UI panels communicate via Qt signals

---

## Target Publications

- **J. Chem. Inf. Model.** — AI-assisted multi-spectral characterization
- **Digital Discovery** (RSC) — ML/AI tools for chemistry
- **J. Cheminformatics** — Software tools + validated datasets

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Research collaboration with BITS Pilani. Built with PyQt5, pyqtgraph, Anthropic Claude API, and Google Gemini API.
=======
# SpectraAI
Spectra AI is a foundation model for molecular structure elucidation. It uses a Multimodal Spectroscopic Transformer to align $^{1}$H, $^{13}$C, and HSQC NMR signals into a latent chemical manifold. An SE(3)-equivariant GNN then refines 3D coordinates with a 0.9987 $R^{2}$ accuracy across a 1.1M compound chemical space.
>>>>>>> 36067c802fdcedf29d1b8200746c21a8219c6603
