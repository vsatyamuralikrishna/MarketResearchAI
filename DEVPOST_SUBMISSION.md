# Devpost Submission — Best Use of the Google Gemini API

Use the sections below when submitting on Devpost. Replace `[Your Name(s)]` with your actual team member names.

---

## Project Name

**Market Research AI**

---

## Project Description

**Market Research AI** is a multi-agent pipeline that produces structured, industry-grade market research reports. Users enter an industry or area (e.g. "FinTech", "Healthcare IT"); the system runs five specialized AI agents in sequence, each powered by the **Google Gemini API**, and outputs a multi-section report (Executive Summary, market categories, segments, behavioral insights, competitive analysis, and a Decision Jury verdict) as PDF or HTML.

The pipeline is designed to reduce hallucination and keep each agent focused: every agent receives only its direct input plus a short summary, so findings don’t “bleed” between steps. The flow is: **Taxonomy Architect** (industry → categories, TAM/SOM, CAGRs) → **Segment Specialist** (per category → primary/secondary segments) → **Behavioral Ethologist** (per segment → Zero Moment of Truth, friction, retention risks) → **Competitive Strategist** (per segment → delivery mechanisms, gaps, moats) → **Decision Jury** (full artifact → conflict check, moat assessment, $1M allocation, segment verdicts). The app is built with **Streamlit** for the UI and **ReportLab** for PDF generation; all agent reasoning and structured outputs are driven by Gemini.

---

## Team Member Names

**[Your Name(s)]** — *Replace with your actual name(s) or team list, e.g. "Jane Doe" or "Jane Doe, John Smith"*

---

## Explanation of How the Gemini API Was Used

The project **meaningfully integrates the Google Gemini API** as the sole LLM backend for the entire research pipeline.

### 1. **API integration**

- The app uses the official **`google-genai`** Python SDK to call the Gemini API.
- A single wrapper module (`src/gemini_client.py`) handles: API key resolution (from environment or Streamlit secrets), client creation, and two call patterns—**`generate()`** for raw text and **`generate_json()`** for structured JSON with retries and robust parsing (including extraction from markdown code blocks and repair of trailing commas).

### 2. **Model usage**

- **Gemini 2.5 Pro** is used for the three agents that need deeper reasoning and synthesis: **Taxonomy Architect** (industry decomposition, TAM/SOM, CAGRs), **Competitive Strategist** (delivery mechanisms, gaps, moats), and **Decision Jury** (conflict check, moat assessment, resource allocation, segment verdicts).
- **Gemini 2.5 Flash** is used for the two high-volume, per-item agents: **Segment Specialist** (run once per category) and **Behavioral Ethologist** (run once per segment), balancing quality with latency and cost.
- Model names are configurable via `config.yaml`, so the project can adapt to future Gemini model names and tiers.

### 3. **Structured outputs**

- Every agent is prompted to return **strict JSON** matching Pydantic schemas. The client uses **system instructions** to enforce role and output format (e.g. “You are a market research Taxonomy Architect… Always respond with valid JSON only”) and **`generate_json()`** to parse and validate responses. This ensures the orchestrator and report builder always receive typed, structured data (categories, segments, pain points, competition gaps, jury verdicts) without manual parsing.

### 4. **Reliability**

- The Gemini client implements **retries with exponential backoff** for rate limits (429) and transient errors (e.g. 503), so the pipeline can complete under load. Failed JSON parsing is handled with fallbacks (e.g. fixing trailing commas, stripping newlines) and clear errors so the pipeline can fail gracefully or be re-run.

### 5. **End-to-end role of Gemini**

- **Taxonomy Architect**: One Gemini call per run; takes the industry string and returns categories with TAM/SOM, CAGRs, and trends.
- **Segment Specialist**: One Gemini call per category; takes category name and context and returns primary/secondary segments and growth drivers.
- **Behavioral Ethologist**: One Gemini call per segment; takes segment name and context and returns ZMOT, alternative paths, and retention killers.
- **Competitive Strategist**: One Gemini call per segment; takes pain points and segment context and returns delivery mechanisms, gaps, and moat analysis.
- **Decision Jury**: One Gemini call at the end; takes the full consolidated artifact (Sections 1–4) and returns conflict check, moat assessment, resource allocation recommendation, and segment verdicts (green/amber/red).

Without the Gemini API, the pipeline would have no reasoning or content generation; Gemini is therefore **essential and central** to the product, not a minor add-on.

---

## Inspiration

We wanted to turn “I need to understand this market” into something you could do in minutes instead of weeks. Real market research usually means spreadsheets, slide decks, and a lot of copy-pasting between frameworks—TAM/SOM, segments, user friction, competitive moats, and finally “where would I put money?” We were inspired by the idea of **agentic AI**: multiple specialized agents, each with a clear role and strict inputs/outputs, so the pipeline stays interpretable and less prone to one big model “making everything up.” The Google Gemini API gave us a single, powerful backend to drive every agent while we focused on pipeline design, structured outputs, and a usable report.

---

## What it does

**Market Research AI** takes an industry or area (e.g. “FinTech”, “Healthcare IT”) and runs a five-step agent pipeline powered by Gemini. In one run it produces a **structured, multi-section report** you can view in the app or download as PDF/HTML.

- **Section 1 — Taxonomy:** Categories, TAM/SOM, historical and projected CAGRs, and key trends.
- **Section 2 — Segments:** For each category, primary and secondary segments and growth drivers.
- **Section 3 — Behavioral:** For each segment, Zero Moment of Truth, alternative paths (workarounds), and retention killers.
- **Section 4 — Competitive:** Delivery mechanisms, product/experience gaps, and moat assessment.
- **Section 5 — Decision Jury:** Conflict check (do growth numbers match user friction?), moat assessment, “if you had $1M where would you invest?”, and segment verdicts (green/amber/red).

Each agent only sees its direct input plus a short summary, so we avoid hallucination bleed-between steps. The result is a single artifact that flows from market structure → segments → behavior → competition → investment recommendation.

---

## How we built it

- **Stack:** Python 3.10+, Streamlit (UI), Google Gemini API via `google-genai`, ReportLab (PDF), Pydantic (schemas).
- **Gemini usage:** One shared client in `src/gemini_client.py` with `generate()` and `generate_json()`, retries with exponential backoff for rate limits, and JSON extraction/repair (markdown code blocks, trailing commas). We use **Gemini 2.5 Pro** for Taxonomy Architect, Competitive Strategist, and Decision Jury, and **Gemini 2.5 Flash** for Segment Specialist and Behavioral Ethologist (many calls per run).
- **Agents:** Five modules in `src/agents/`, each with a system instruction and a prompt template that asks for strict JSON; outputs are parsed and validated into Pydantic models.
- **Orchestrator:** `src/orchestrator.py` runs the pipeline sequentially (Taxonomy → Segment per category → Behavioral per segment → Competitive per segment → Jury on full artifact), merges results into one artifact, and optionally writes `output/artifact.json`.
- **Report:** `src/report/builder.py` turns the artifact into PDF and HTML with an executive summary and Sections 1–5. The Streamlit app lets users set industry, optional limits (e.g. max categories), run the pipeline with progress updates, and download the report.

---

## Challenges we ran into

- **Structured JSON from the model:** Gemini sometimes returned JSON inside markdown code fences or with trailing commas. We added `extract_json_block()` and `_try_fix_json()` in the client so we could reliably parse without failing the whole pipeline.
- **Keeping agents focused:** We had to design prompts and data flow so each agent only receives what it needs (e.g. Segment Specialist gets category + summary, not the full prior report). That required clear handoffs and a single “summary” string passed forward to avoid context bloat and cross-step hallucination.
- **Rate limits and reliability:** With many segments, we hit 429s. We implemented retries with exponential backoff and made model names configurable so we could tune Pro vs. Flash per agent and stay within limits.
- **Decision Jury on a large artifact:** Passing the full artifact as JSON in the prompt could get long. We kept the Jury prompt to a single “ARTIFACT (JSON)” block and asked for concise answers plus segment-level verdicts so the output stayed parseable and useful.

---

## Accomplishments that we're proud of

- **End-to-end agentic pipeline** that goes from one industry string to a full, downloadable report with taxonomy, segments, behavior, competition, and investment verdicts—all driven by Gemini.
- **Strict separation of agent roles** and data flow, so the pipeline is interpretable and each section has a clear “author” (agent).
- **Robust Gemini integration:** one client, Pro/Flash split, retries, and JSON parsing that handles real-world model output.
- **Usable output:** Pydantic-backed artifact, PDF/HTML report, and Streamlit UI so stakeholders can run research and download results without touching code.

---

## What we learned

- **System instructions and output format matter:** Telling each agent “Respond with valid JSON only” and giving a concrete schema in the prompt made structured parsing reliable without needing separate tool-calling or schema enforcement APIs.
- **Pro vs. Flash is a real tradeoff:** Using Flash for high-volume, per-segment agents kept latency and cost down while Pro for taxonomy, competition, and jury gave us the reasoning quality we wanted for synthesis and verdicts.
- **Isolating context reduces hallucination:** Passing only direct input + short summary to each agent (instead of the full transcript) kept outputs grounded and made it easier to debug which step went wrong when something looked off.

---

## What's next for Agentic Deep Market Research

- **Agentic Go To Market strategy:** Add a dedicated GTM agent (or agent phase) that consumes the research artifact and produces actionable go-to-market strategy—positioning, channels, pricing signals, launch sequence, and success metrics—so the pipeline goes from market understanding to execution playbook.
- **Dynamic research with user-guided navigation:** Move from a single linear run to a **multi-branch research flow** where users can steer the pipeline: e.g. drill into one category or segment, add a new branch for a sub-segment, re-run only from a chosen step, or compare branches side-by-side. Research becomes a navigable tree (industry → categories → segments → sub-segments) with user-guided expansion and on-demand agent runs per branch.

---

*After filling in team member names, copy each section into the corresponding fields on your Devpost submission page.*
