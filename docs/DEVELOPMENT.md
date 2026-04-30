# SpectraAI — Development Guide

## Getting Started

### Prerequisites

- Python 3.10+
- PyQt5 (desktop UI)
- pyqtgraph (spectrum plotting)
- numpy, scipy (numerical)
- anthropic / google-generativeai (AI backends)
- Optional: rdkit-pypi (2D structure rendering)

### Setup

```bash
git clone <repo-url>
cd SpectraAI
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env    # add your API keys
python run.py --debug
```

### Running Tests

```bash
# Full suite
pytest tests/ -v

# Individual modules
pytest tests/test_core.py -v
pytest tests/test_parsers.py -v
pytest tests/test_validation.py -v
pytest tests/test_ai.py -v

# Coverage
pytest tests/ --cov=spectra_ai --cov-report=html
open htmlcov/index.html
```

---

## Architecture Overview

```
User Input → Parsers → Core Data Models → AI Engine → Interpretation
                                        → Validation → Report
                                        → Text Gen   → Characterization
```

### Layer Responsibilities

| Layer | Directory | Role |
|-------|-----------|------|
| **Core** | `core/` | Immutable data models — Molecule, NMRData, IRData, MSData, etc. |
| **Parsers** | `parsers/` | Convert raw text from experimental sections into core models |
| **AI Engine** | `ai/` | LLM client + domain interpreters + prompt templates |
| **Validation** | `validation/` | Rule-based checkers with weighted scoring |
| **Prediction** | `prediction/` | Scaffold enumeration and candidate ranking |
| **UI** | `ui/` | PyQt5 panels, widgets, styles |
| **Utils** | `utils/` | Reference data, formula helpers, SMILES utilities |

### Data Flow

1. User pastes text → `NMRTextParser.parse_h1()` → `NMRData`
2. `NMRData` → `NMRInterpreter.interpret_h1()` → AI JSON response
3. `Molecule` + all data → `ValidationEngine.validate()` → `ValidationReport`
4. All results → `CharacterizationWriter.generate()` → publication text

---

## Adding a New Scaffold

1. Add reference ranges to `utils/nmr_reference.py` → `NMR_REFERENCE_RANGES`
2. Create `data/scaffold_references/<scaffold>.json`
3. Add to `core/molecule.py` → `SCAFFOLD_FAMILIES`
4. Update prompt templates in `ai/prompts/` to recognize the new family
5. Add validation test cases in `tests/test_validation.py`

## Adding a New Validation Check

1. Create `validation/<check_name>_checker.py`
2. Implement `check(self, molecule, **data) → ValidationCheck`
3. Register in `validation/validation_engine.py` → `__init__`
4. Add weight in `core/validation_report.py` → `CATEGORY_WEIGHTS`
5. Write tests in `tests/test_validation.py`

## Adding a New AI Prompt

1. Create `ai/prompts/<task>.py` with `SYSTEM_PROMPT` and `build_user_prompt()`
2. Create interpreter class in `ai/<task>_interpreter.py`
3. Wire into `AnalysisWorker` in `ui/main_window.py`
4. Add result handler in `MainWindow._on_<task>_result()`

---

## Code Conventions

- **Data models:** Python dataclasses with `to_dict()` / `from_dict()` serialization
- **AI responses:** Always structured JSON parsed from LLM output
- **Validation checks:** Standard `check()` interface returning `ValidationCheck`
- **UI signals:** Qt signals for inter-panel communication
- **Naming:** `snake_case` for files/functions, `PascalCase` for classes
- **Imports:** Absolute imports from `spectra_ai.*`

## Branching

- `main` — stable releases
- `develop` — integration branch
- `feature/<name>` — new features
- `fix/<name>` — bug fixes

---

## Key Files

| File | Lines | Role |
|------|-------|------|
| `ai/llm_client.py` | ~270 | Unified Claude/Gemini API client |
| `ai/nmr_interpreter.py` | ~240 | ¹H/¹³C NMR interpretation orchestrator |
| `parsers/nmr_text_parser.py` | ~270 | Critical journal text → NMR peak parser |
| `core/molecule.py` | ~290 | Central data model with completeness tracking |
| `core/nmr_data.py` | ~300 | NMR peaks, regions, spectrum generation |
| `ui/main_window.py` | ~480 | Application orchestrator + analysis pipeline |
| `ui/input_panel.py` | ~300 | Data entry with completeness ring |
| `validation/validation_engine.py` | ~110 | Check orchestrator + report builder |
