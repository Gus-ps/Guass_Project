# LLM Stock Insights — Backend MVP

Minimal backend function scaffold for extracting multi-source company information and generating LLM-based insights.

## What this repo provides
- Functions to validate tickers
- Fetchers: Yahoo (via yfinance), Web (Wikipedia), Reddit (Pushshift), YouTube (Google Data API when API key provided)
- LLM clients: Anthropic wrapper (required), optional OpenAI wrapper (fallback/comparator)
- An orchestrator that runs the pipeline and returns a markdown report

## Structure
- `src/backend.py`: consolidated backend functions (fetchers, LLM wrappers, orchestration)
- `scripts/run_demo.py`: demo script to test the pipeline
- `.env.example`: environment variables template
- `requirements.txt`: Python dependencies

## How to use (locally)
1. Copy `.env.example` to `.env` and fill keys (ANTHROPIC_API_KEY required, optional YT/OPENAI keys).
2. Create a venv and install requirements:
   ```powershell
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   pip install -r requirements.txt
   ```
3. Run the demo:
   ```powershell
   python .\\scripts\\run_demo.py AAPL
   ```

## Note
This repo focuses on backend functions only (no HTTP endpoints yet). Many fetchers fall back gracefully when API keys are missing; add keys for better results.
