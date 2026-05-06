# COT-Trace

**Live web reasoning auditor** — scrapes AI research blogs with Apify, asks Claude a question, then audits whether every reasoning step is actually supported by the evidence.

---

## Setup (5 min)

```bash
git clone <repo>
cd sensetrace
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your tokens
```

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
Claude Pass 1     (structured reasoning JSON)
   ↓
Claude Pass 2     (step-level audit labels)
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
