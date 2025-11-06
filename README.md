# LLM Stock Insights — Backend MVP

Minimal backend function scaffold for extracting multi-source company information and generating LLM-based insights.

## What this repo provides
- Functions to validate tickers
- Fetchers: Yahoo (via yfinance), Web (Wikipedia), YouTube (Google Data API when API key provided)
- LLM clients: Anthropic wrapper (required),
- An orchestrator that runs the pipeline and returns a markdown report

## Structure
- `src/backend.py`: consolidated backend functions (fetchers, LLM wrappers, orchestration)
- `scripts/run_demo.py`: demo script to test the pipeline
- `.env.example`: environment variables template
- `requirements.txt`: Python dependencies

## How to use (locally)
1. Copy `.env.example` to `.env` and fill keys (ANTHROPIC_API_KEY required, `YOUTUBE_API_KEY`).
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

# TubePulse (Guass_Project)

A lightweight developer demo that turns YouTube conversations and public data into concise, analyst-style investment reports using LLMs.

This project fetches company summaries and metrics (Yahoo Finance, Wikipedia), collects YouTube videos/comments, filters and analyzes them, and asks an LLM to synthesize everything into a readable report.

> Note: The repository started as a take-home project and was iteratively improved to include YouTube comment filtering, improved prompts, and a clean frontend landing UI.

---

## What it does

- Fetches company metadata and financial metrics (via Yahoo Finance / yfinance and other services).
- Collects recent YouTube videos and top comments relevant to the ticker.
- Filters and scores YouTube comments to find higher-quality investor-focused commentary.
- Uses an LLM (Anthropic model by default in this repo) to synthesize an 8-section markdown report: Executive Summary, Company Overview, Financial Health & Metrics (table), Recent Performance, Market Sentiment, Key Concerns & Risks, Positive Signals & Opportunities, Investment Outlook.  
- Frontend (React + Vite) shows a clean landing page with a centered search bar and renders the report with tables and embedded YouTube players.

---

## Project structure

- `src/` - Python backend (FastAPI) and business logic
   - `src/api.py` - FastAPI endpoint(s) (POST /report)
   - `src/backend.py` - data fetching, filtering, and LLM orchestration
   - `src/prompts.py` - LLM prompt templates (XML-like structured prompts)
   - `requirements.txt` - Python dependencies

- `frontend/` - React app (Vite)
   - `frontend/src/App.jsx` - landing page + frontend logic
   - `frontend/src/components/SearchBar.jsx` - search form
   - `frontend/src/components/ReportView.jsx` - report rendering, YouTube embed, markdown renderer
   - `frontend/src/styles.css` - styling and layout

- `README.md` - this file

---

## Technologies used

- Backend: Python 3.11+ (or 3.10/3.12 compatible), FastAPI, uvicorn, requests, yfinance, beautifulsoup4
- LLM: Anthropic (Claude) via their SDK (configurable via `ANTHROPIC_API_KEY`)
- Frontend: React 18, Vite, plain CSS
- APIs: Yahoo Finance (yfinance), Wikipedia MediaWiki, YouTube Data API v3

---

## Environment & API keys

Set the following environment variables in your shell or in a `.env` file for the frontend (see below):

- `ANTHROPIC_API_KEY` - API key for Anthropic/Claude (used by the backend LLM calls)
- `YOUTUBE_API_KEY` - YouTube Data API v3 key (used to fetch videos/comments)

Frontend needs an environment variable to target the backend (optional):
- `VITE_API_URL` - example: `http://localhost:8000` (defaults to `http://localhost:8000`)

Security note: Never commit API keys to git. Use environment variables or a secrets manager.

---

## How to get a YouTube Data API key

To fetch videos and comments the project uses the YouTube Data API v3. Follow these steps to create an API key and plug it into the project:

1. Open the Google Cloud Console: https://console.cloud.google.com/
2. Create (or select) a project.
3. In the left-hand menu, go to "APIs & Services" → "Library" and search for **YouTube Data API v3**. Click it and then click **Enable**.
4. After enabling, go to "APIs & Services" → "Credentials" and click **Create credentials** → **API key**.
5. Copy the generated API key. 


Once you have the key, add it to your `.env` (or export it in your environment) as:

```
YOUTUBE_API_KEY=your_api_key_here
```

Note: If you do not provide a `YOUTUBE_API_KEY`, the app will still produce reports using Yahoo/Wikipedia/metrics, but social sentiment (YouTube) sections will be empty or limited.

## Install (backend)

Open PowerShell at the project root (`C:\Users\gusta\OneDrive\Desktop\Guass_Project`) and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

If you don't want to create a venv, install globally (not recommended):

```powershell
pip install -r requirements.txt
```

---

## Install (frontend)

Open PowerShell in the `frontend` folder and install dependencies:

```powershell
cd frontend
npm install
```

The frontend expects a `VITE_API_URL` environment variable during development if your backend runs on a non-default host or port. You can create a `.env` file in `frontend/` with:

```
VITE_API_URL=http://localhost:8000
```

---

## Run (development)

1. Start the backend from the project root (must run from the parent of `src`):

```powershell
python -m uvicorn src.api:app --reload --port 8000
```

Important: Run the command from the project root and NOT from inside the `src/` folder to avoid `ModuleNotFoundError: No module named 'src'`.

2. Start the frontend (in a separate terminal):

```powershell
cd frontend
npm run dev
```

Open the browser at the address printed by Vite (usually `http://localhost:5173` or `http://localhost:5174`).

---

## Usage

- On the landing page, enter a stock ticker symbol (e.g., `AAPL`) and click "Generate".
- The backend will fetch data, call the LLM, and return a structured markdown report.
- The frontend renders the report with tables; YouTube videos included in the report are embedded with the official YouTube player.

---

## Troubleshooting & Notes

- ModuleNotFoundError: No module named 'src' — ensure you run `python -m uvicorn src.api:app` from the project root (parent of `src`).
- If YouTube quotas are exceeded, the app will still build a report using Yahoo/Wikipedia/metrics, but social sentiment sections may be empty.
- LLM output may contain formatting quirks; prompts are stored in `src/prompts.py` and are where to tune tone, sections, and table requests.

---

## Development notes

- Prompts: `src/prompts.py` contains two main prompt builders:
   - `build_analyze_comments_prompt` - analyzes YouTube comments and returns a JSON structure
   - `build_compare_prompt` - synthesizes Yahoo/Wikipedia/metrics/social media into an 8-section markdown report (now structured via XML-like tags in the prompt)

- Frontend markdown rendering: `frontend/src/components/ReportView.jsx` has a small custom markdown renderer that supports headers, lists, bold, and GitHub-style tables. Bold parsing and table rendering were improved during development.

- YouTube embed: The app extracts the video ID and uses the official `https://www.youtube.com/embed/{id}` iframe for embedding videos. If it cannot parse an ID it shows a link instead.

---
