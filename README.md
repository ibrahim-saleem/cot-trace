# COT-Trace

**Live web reasoning auditor** — scrapes AI research blogs with Apify, answers questions using local extractive reasoning, then audits whether each reasoning step is supported by evidence.

---

## Setup (5 min)

```bash
git clone <repo>
cd sensetrace
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your tokens
```

Only `APIFY_TOKEN` is needed.
No Groq/Anthropic/OpenAI keys are required.

---

## Before the demo — pre-scrape (do this first!)

```bash
python -m src.apify_ingest
```

This scrapes Anthropic, OpenAI, and DeepMind blogs and caches them to `data/raw/documents.json`.
Subsequent runs skip the network and load from cache — **demo is instant**.

---

## Run the app

```bash
streamlit run app.py
```

## Deploy on Streamlit Community Cloud (no local run)

1. Push this repository to GitHub.
2. Go to Streamlit Community Cloud and click **New app**.
3. Select this repo, branch `main`, and entrypoint file `app.py`.
4. Click **Deploy**.

Notes:
- This app runs in local-free mode (no Anthropic/Groq keys).
- It reads cached data from `data/raw/documents.json`.
- If you want cloud-side re-scraping later, add `APIFY_TOKEN` in Streamlit app secrets.

---

## Demo flow (2 min)

1. Open sidebar → tokens are pre-filled from `.env`
2. Click **Load / refresh sources** → shows cached doc counts instantly
3. Type: *"What has Anthropic published about reasoning faithfulness?"*
4. Click **Audit reasoning →**
5. Watch: answer → audit score → color-coded steps → clickable source links

---

## Architecture

```
Apify scrape (pre-cached)
   ↓
TF-IDF retriever  (scikit-learn, no infra needed)
   ↓
Local Pass 1      (extractive reasoning trace)
   ↓
Local Pass 2      (step-level overlap audit labels)
   ↓
Streamlit UI      (scores + clickable citations)
```

---

## Audit labels

| Label | Meaning |
|---|---|
| 🟢 supported | Evidence directly backs the step |
| 🟡 weak | Partial or indirect support |
| 🔴 unsupported | No supporting evidence found |
| 🔴 contradictory | Evidence conflicts with the step |
| 🟠 speculative | Step goes beyond what evidence says |
