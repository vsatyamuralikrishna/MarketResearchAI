# Market Research AI

Multi-agent pipeline for industry market research: **Taxonomy Architect → Segment Specialist → Behavioral Ethologist → Competitive Strategist → Decision Jury**. Each agent is isolated (receives only its direct input + short summary) to avoid hallucination bleed-over. Output is a structured, multi-page PDF/HTML report.

## Tech Stack

- **Python 3.10+**
- **Streamlit** — UI (input industry, progress, report viewer/download)
- **Google Gemini API** (`google-genai` SDK) — Agents use Gemini 2.5 (Pro for taxonomy/competitive/jury, Flash for segments/behavioral). See [Gemini API models](https://ai.google.dev/gemini-api/docs/models).
- **ReportLab** — PDF report generation
- **Pydantic** — Structured agent outputs

## Setup

1. **Clone / open the project** and create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set your Gemini API key:**

   - Copy `.env.example` to `.env` and set `GEMINI_API_KEY=your_key`, or
   - In Streamlit Cloud / hosted app: use Secrets and set `GEMINI_API_KEY`.

4. **Run the app:**

   ```bash
   streamlit run streamlit_app.py
   ```

   Open the URL shown (e.g. http://localhost:8501).

## Usage

1. Enter an **Industry / Area** (e.g. "FinTech", "Healthcare IT").
2. Optionally set **Options** (max categories / segments per category) for a faster demo.
3. Click **Run Research**. The pipeline runs sequentially; progress is shown.
4. When done, use the **Report** tabs to view Executive Summary, Section 1–5, and **Download** for PDF or HTML.

## Pipeline Overview

| Step | Agent | Input | Output |
|------|--------|--------|--------|
| 1 | Taxonomy Architect | Industry | Categories, TAM/SOM, CAGRs, trends |
| 2 | Segment Specialist | Per category | Primary/secondary segments, growth drivers |
| 3 | Behavioral Ethologist | Per segment | ZMOT, alternative paths, retention killers |
| 4 | Competitive Strategist | Per segment + pain points | Delivery, gaps, moat |
| 5 | Decision Jury | Full artifact | Conflict check, moat, $1M allocation, verdicts |

## Configuration

- **`config.yaml`** (optional): Override Gemini model names and limits (e.g. `max_categories`, `max_segments_per_category`). See `config.yaml` in the repo.
- **Environment**: `GEMINI_API_KEY` is required (`.env` or Streamlit secrets).

## Project Layout

- `streamlit_app.py` — Streamlit entry
- `src/models.py` — Pydantic schemas (Section 1–4, Jury)
- `src/gemini_client.py` — Gemini API wrapper (retries, JSON parsing)
- `src/agents/` — Taxonomy Architect, Segment Specialist, Behavioral Ethologist, Competitive Strategist, Decision Jury
- `src/orchestrator.py` — Pipeline runner and artifact merge
- `src/report/builder.py` — PDF and HTML report builder
- `src/config.py` — Config loader
- `config.yaml` — Model names and limits
- `output/` — Written artifact JSON (after a run)

## Errors and Rate Limits

- **GEMINI_API_KEY not set**: Add it to `.env` or Streamlit secrets.
- **Rate limits (429)**: The client retries with backoff; reduce concurrency or wait and re-run.
- **Parsing errors**: If an agent returns invalid JSON, the pipeline will raise; you can inspect `output/artifact.json` for partial results if you add error handling.

## License

MIT.
