"""
app.py  —  COT-Trace Streamlit UI
Run: streamlit run app.py
"""
import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

from src.apify_ingest import load_or_scrape
from src.retrieve import Retriever
from src.reason import generate_trace, audit_trace
from src.schemas import AuditLabel

load_dotenv()

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="COT-Trace",
    page_icon="🔍",
    layout="wide",
)

LABEL_COLORS = {
    "supported":     ("🟢", "#d4edda", "#155724"),
    "weak":          ("🟡", "#fff3cd", "#856404"),
    "unsupported":   ("🔴", "#f8d7da", "#721c24"),
    "contradictory": ("🔴", "#f8d7da", "#721c24"),
    "speculative":   ("🟠", "#fde8d8", "#7d3c10"),
}

# ── sidebar: config ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ COT-Trace")
    st.caption("Live web reasoning auditor")
    st.divider()

    apify_token  = st.text_input("Apify token",   value=os.getenv("APIFY_TOKEN", ""),  type="password")
    anthropic_key = st.text_input("Groq key", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password")

    st.divider()
    force_rescrape = st.checkbox("Force re-scrape (slow)", value=False)

    if st.button("🔄 Load / refresh sources", use_container_width=True):
        if not apify_token:
            st.error("Apify token required")
        else:
            with st.spinner("Loading documents…"):
                st.session_state["docs"] = load_or_scrape(apify_token, force=force_rescrape)
                st.session_state["retriever"] = Retriever(st.session_state["docs"])
            st.success(f"Loaded {len(st.session_state['docs'])} documents")

    if "docs" in st.session_state:
        docs = st.session_state["docs"]
        sources = {}
        for d in docs:
            sources[d.source] = sources.get(d.source, 0) + 1
        for src, count in sources.items():
            st.caption(f"• {src}: {count} pages")

# ── main ─────────────────────────────────────────────────────────────────────
st.title("🔍 COT-Trace")
st.markdown("*Ask a question over live web data — then see whether Claude's reasoning is actually supported by the evidence.*")
st.divider()

question = st.text_input(
    "Your question",
    placeholder="e.g. What has Anthropic published about reasoning faithfulness?",
)

run_btn = st.button("Audit reasoning →", type="primary", disabled=not question)

if run_btn:
    if "retriever" not in st.session_state:
        st.error("Load sources first (sidebar).")
        st.stop()
    if not anthropic_key:
        st.error("Anthropic API key required.")
        st.stop()

    client = Groq(api_key=anthropic_key)
    retriever: Retriever = st.session_state["retriever"]

    with st.spinner("Retrieving relevant evidence…"):
        chunks = retriever.query(question)

    if not chunks:
        st.warning("No relevant chunks found. Try a different question or reload sources.")
        st.stop()

    with st.spinner("Generating reasoning trace…"):
        trace = generate_trace(client, question, chunks)

    with st.spinner("Auditing each reasoning step…"):
        trace, score = audit_trace(client, trace, chunks)

    # ── layout ───────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        # answer
        st.subheader("Answer")
        st.markdown(f"> {trace.answer}")

        conf_pct = int(trace.confidence * 100)
        st.caption(f"Model confidence: {conf_pct}%")
        if trace.risk_flags and trace.risk_flags != ["none"]:
            st.warning("⚠️ Risk flags: " + ", ".join(trace.risk_flags))

        st.divider()

        # audit score banner
        st.subheader("Audit score")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Overall",       f"{int(score.overall * 100)}%")
        m2.metric("Grounding",     f"{int(score.grounding_score * 100)}%")
        m3.metric("Ev. coverage",  f"{int(score.evidence_coverage * 100)}%")
        m4.metric("Contradictions", score.contradiction_count)

        st.divider()

        # reasoning steps
        st.subheader("Reasoning trace")
        for step in trace.steps:
            emoji, bg, fg = LABEL_COLORS.get(step.audit_label, ("⚪", "#f0f0f0", "#333"))
            with st.container():
                st.markdown(
                    f"""<div style="background:{bg};border-radius:8px;padding:12px 16px;margin-bottom:10px;">
                    <span style="font-size:0.8rem;font-weight:600;color:{fg}">
                        {emoji} Step {step.step_id} · {step.audit_label.upper()} · {step.label}
                    </span>
                    <p style="margin:6px 0 4px;color:#111;">{step.text}</p>
                    <p style="font-size:0.8rem;color:{fg};margin:0;font-style:italic">{step.audit_explanation}</p>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if step.citations:
                    for c in step.citations:
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;📎 [{c.title}]({c.url}) — *\"{c.snippet[:120]}…\"*"
                        )

    with col_right:
        st.subheader("Sources used")
        seen_urls = set()
        for chunk in chunks:
            if chunk.url in seen_urls:
                continue
            seen_urls.add(chunk.url)
            with st.expander(f"{chunk.source} — {chunk.title[:60]}"):
                st.markdown(f"[Open source ↗]({chunk.url})")
                st.caption(chunk.text[:400] + "…")
