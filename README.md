
# Agentic Visuals — Hello World (No CrewAI)

This is a **minimal runnable scaffold** of your agentic pipeline that turns a teacher prompt + year into a **sequence of visual panels** and exports **PDF/PPTX**. It's offline and uses **stub agents** (no API calls), so you can run it immediately.

## Environment Requirements

- **Python**: 3.10+ (tested with 3.12)
- **Pydantic**: Locked to v1.10.13 for compatibility
- **Streamlit**: 1.48.* for Pydantic v1 support
- **OS**: Cross-platform (Windows/Linux/macOS)

## Quick start

```bash
cd /path/to/StAnify_4
python -m venv .venv

# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run streamlit_app/app.py
```

## Development Setup

For development with code quality tools:

```bash
# Install development dependencies
pip install -r requirements.txt

# Set up pre-commit hooks
pre-commit install

# Format code
black .
ruff check . --fix

# Run tests
pytest
```

The Streamlit app runs the end-to-end demo in-process (no separate FastAPI server needed for this hello-world).

## Project layout

```
agentic-visuals-hello/
├── assets/                  # placeholder images
├── kb/                      # static curriculum KB
├── src/agentic_flow/        # contracts + tiny pipeline + exporters
├── streamlit_app/           # UI
├── templates/               # LLM prompt templates (for later swap-in)
├── requirements.txt
└── README.md
```

## Next steps

- Swap stub agents with real LLM calls and your SDXL backend.
- Replace `kb/year1.yaml` with your full dataset.
- (Optional) Split into FastAPI + workers if you want async jobs.
