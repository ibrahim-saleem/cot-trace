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

# ── advanced css animations & styling ─────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    /* ─── Global Animations ─── */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px rgba(100, 200, 255, 0.3); }
        50% { box-shadow: 0 0 20px rgba(100, 200, 255, 0.6); }
    }
    
    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes bounceIn {
        0% { transform: scale(0.3); opacity: 0; }
        50% { opacity: 1; }
        70% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* ─── Main Container Styling ─── */
    .main {
        animation: fadeIn 0.8s ease-in-out;
    }
    
    /* ─── Header & Title Styling ─── */
    h1 {
        animation: fadeInUp 0.6s ease-out;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        letter-spacing: -1px;
    }
    
    h2 {
        animation: slideInRight 0.5s ease-out;
        border-left: 4px solid #667eea;
        padding-left: 12px;
        transition: all 0.3s ease;
    }
    
    h2:hover {
        border-left-color: #764ba2;
        padding-left: 16px;
    }
    
    /* ─── Input Field Styling ─── */
    .stTextInput input {
        animation: fadeIn 0.6s ease-out 0.1s both;
        border: 2px solid transparent !important;
        border-radius: 12px !important;
        background: linear-gradient(white, white) padding-box, linear-gradient(135deg, #667eea, #764ba2) border-box;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
    }
    
    .stTextInput input:focus {
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.25) !important;
        transform: translateY(-2px);
    }
    
    /* ─── Button Styling ─── */
    .stButton > button {
        animation: fadeIn 0.6s ease-out 0.2s both;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button:before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.2);
        transition: left 0.5s ease;
    }
    
    .stButton > button:hover:before {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.5);
    }
    
    .stButton > button:active {
        transform: translateY(-1px) scale(0.98);
    }
    
    /* ─── Divider Styling ─── */
    hr {
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        border: none;
        height: 2px;
        animation: slideUp 0.6s ease-out;
    }
    
    /* ─── Sidebar Styling ─── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f5f7ff 0%, #f0f3ff 100%);
        animation: slideInLeft 0.5s ease-out;
    }
    
    [data-testid="stSidebar"] h1 {
        animation: bounceIn 0.7s ease-out;
    }
    
    /* ─── Metric Cards ─── */
    [data-testid="metric-container"] {
        animation: fadeInUp 0.6s ease-out both;
        background: linear-gradient(135deg, #f5f7ff 0%, #fff 100%);
        border: 2px solid rgba(102, 126, 234, 0.1);
        border-radius: 12px;
        padding: 16px;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    
    [data-testid="metric-container"]:hover {
        border-color: rgba(102, 126, 234, 0.3);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
        transform: translateY(-4px);
    }
    
    /* ─── Container Styling ─── */
    .stContainer {
        animation: slideUp 0.5s ease-out;
    }
    
    /* ─── Expander Styling ─── */
    [data-testid="stExpander"] {
        animation: fadeIn 0.5s ease-out;
        border: 2px solid rgba(102, 126, 234, 0.1) !important;
        border-radius: 12px !important;
        transition: all 0.3s ease;
    }
    
    [data-testid="stExpander"]:hover {
        border-color: rgba(102, 126, 234, 0.3) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
    }
    
    /* ─── Caption & Markdown ─── */
    .stCaption, p, span {
        animation: fadeIn 0.6s ease-out;
    }
    
    /* ─── Warning/Error/Success Boxes ─── */
    [data-testid="stWarning"], [data-testid="stError"], [data-testid="stSuccess"] {
        animation: slideInRight 0.5s ease-out !important;
        border-radius: 10px !important;
        transition: all 0.3s ease;
    }
    
    [data-testid="stWarning"]:hover, [data-testid="stError"]:hover, [data-testid="stSuccess"]:hover {
        transform: translateX(4px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
    }
    
    /* ─── Step Card Animation ─── */
    .step-card {
        animation: fadeInUp 0.5s ease-out;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border: 2px solid transparent;
        background-size: 200% 200%;
        background-position: 0% 50%;
        transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        position: relative;
        overflow: hidden;
    }
    
    .step-card:before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        animation: shimmer 3s infinite;
    }
    
    .step-card:hover {
        transform: translateX(6px) translateY(-4px);
        box-shadow: 0 12px 28px rgba(102, 126, 234, 0.2);
    }
    
    .step-card.supported {
        border-color: #10b981;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(16, 185, 129, 0.02) 100%);
    }
    
    .step-card.weak {
        border-color: #f59e0b;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(245, 158, 11, 0.02) 100%);
    }
    
    .step-card.unsupported, .step-card.contradictory {
        border-color: #ef4444;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.05) 0%, rgba(239, 68, 68, 0.02) 100%);
    }
    
    .step-card.speculative {
        border-color: #f97316;
        background: linear-gradient(135deg, rgba(249, 115, 22, 0.05) 0%, rgba(249, 115, 22, 0.02) 100%);
    }
    
    /* ─── Links & Citations ─── */
    a {
        color: #667eea;
        text-decoration: none;
        transition: all 0.3s ease;
        position: relative;
    }
    
    a:after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 0;
        height: 2px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        transition: width 0.3s ease;
    }
    
    a:hover {
        color: #764ba2;
    }
    
    a:hover:after {
        width: 100%;
    }
    
    /* ─── Spinner/Loading Animation ─── */
    .stSpinner {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    /* ─── Responsive Animation Delays ─── */
    [data-testid="stVerticalBlock"] > div:nth-child(1) { animation-delay: 0s; }
    [data-testid="stVerticalBlock"] > div:nth-child(2) { animation-delay: 0.1s; }
    [data-testid="stVerticalBlock"] > div:nth-child(3) { animation-delay: 0.2s; }
    [data-testid="stVerticalBlock"] > div:nth-child(4) { animation-delay: 0.3s; }
    [data-testid="stVerticalBlock"] > div:nth-child(n+5) { animation-delay: 0.4s; }
    
    /* ─── Checkbox & Radio Styling ─── */
    [data-testid="stCheckbox"] {
        animation: fadeIn 0.6s ease-out;
        transition: all 0.3s ease;
    }
    
    [data-testid="stCheckbox"]:hover {
        transform: scale(1.02);
    }
    
    /* ─── Color-coded Step Badges ─── */
    .step-label-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        text-transform: uppercase;
    }
    
    .step-label-badge:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    </style>
    """, unsafe_allow_html=True)

inject_css()

LABEL_COLORS = {
    "supported":     ("🟢", "#d4edda", "#155724", "supported"),
    "weak":          ("🟡", "#fff3cd", "#856404", "weak"),
    "unsupported":   ("🔴", "#f8d7da", "#721c24", "unsupported"),
    "contradictory": ("🔴", "#f8d7da", "#721c24", "contradictory"),
    "speculative":   ("🟠", "#fde8d8", "#7d3c10", "speculative"),
}

# ── sidebar: config ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ COT-Trace", help="Live web reasoning auditor")
    st.caption("🔍 Live web reasoning auditor")
    st.divider()

    apify_token  = st.text_input("Apify token",   value=os.getenv("APIFY_TOKEN", ""),  type="password", key="apify")
    anthropic_key = st.text_input("Groq key", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password", key="groq")

    st.divider()
    force_rescrape = st.checkbox("⚡ Force re-scrape (slow)", value=False)

    if st.button("🔄 Load / refresh sources", use_container_width=True, key="load_btn"):
        if not apify_token:
            st.error("🚨 Apify token required")
        else:
            with st.spinner("📥 Loading documents…"):
                st.session_state["docs"] = load_or_scrape(apify_token, force=force_rescrape)
                st.session_state["retriever"] = Retriever(st.session_state["docs"])
            st.success(f"✅ Loaded {len(st.session_state['docs'])} documents")

    if "docs" in st.session_state:
        st.divider()
        st.markdown("**📚 Sources**")
        docs = st.session_state["docs"]
        sources = {}
        for d in docs:
            sources[d.source] = sources.get(d.source, 0) + 1
        for src, count in sources.items():
            st.caption(f"• {src}: {count} pages")

# ── main ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <h1 style="margin-bottom: 10px;">🔍 COT-Trace</h1>
    <p style="font-size: 1.1rem; color: #666; font-weight: 500; animation: fadeIn 0.8s ease-out 0.2s both;">
        Ask a question over live web data — then see whether Claude's reasoning is actually supported by the evidence.
    </p>
</div>
""", unsafe_allow_html=True)
st.divider()

col1, col2 = st.columns([0.85, 0.15])
with col1:
    question = st.text_input(
        "Your question",
        placeholder="e.g. What has Anthropic published about reasoning faithfulness?",
        key="question_input",
    )

with col2:
    run_btn = st.button("Audit 🚀", type="primary", disabled=not question, use_container_width=True)

if run_btn:
    if "retriever" not in st.session_state:
        st.error("🚨 Load sources first (sidebar).")
        st.stop()
    if not anthropic_key:
        st.error("🚨 Anthropic API key required.")
        st.stop()

    client = Groq(api_key=anthropic_key)
    retriever: Retriever = st.session_state["retriever"]

    with st.spinner("🔎 Retrieving relevant evidence…"):
        chunks = retriever.query(question)

    if not chunks:
        st.warning("⚠️ No relevant chunks found. Try a different question or reload sources.")
        st.stop()

    with st.spinner("🧠 Generating reasoning trace…"):
        trace = generate_trace(client, question, chunks)

    with st.spinner("✅ Auditing each reasoning step…"):
        trace, score = audit_trace(client, trace, chunks)

    # ── layout ───────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        # answer section
        st.markdown("## 💡 Answer", help="The model's answer to your question")
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.05) 100%);
            border-left: 5px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            animation: slideInRight 0.6s ease-out;
            transition: all 0.3s ease;
        " onmouseover="this.style.boxShadow='0 8px 24px rgba(102, 126, 234, 0.2)'" 
           onmouseout="this.style.boxShadow='none'">
            <p style="font-size: 1.05rem; color: #111; line-height: 1.6; margin: 0;">{trace.answer}</p>
        </div>
        """, unsafe_allow_html=True)

        conf_pct = int(trace.confidence * 100)
        col_conf, col_empty = st.columns([0.3, 0.7])
        with col_conf:
            st.metric("📊 Confidence", f"{conf_pct}%")
        
        if trace.risk_flags and trace.risk_flags != ["none"]:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
                border-left: 5px solid #ef4444;
                border-radius: 8px;
                padding: 14px 16px;
                animation: slideInRight 0.6s ease-out 0.1s both;
            ">
                <span style="font-weight: 600; color: #dc2626;">⚠️ Risk Flags</span>
                <p style="margin: 6px 0 0; color: #7f1d1d;">{', '.join(trace.risk_flags)}</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # audit score banner
        st.markdown("## 📈 Audit Score", help="Quality metrics for the reasoning")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Overall", f"{int(score.overall * 100)}%", delta=None, help="Overall audit score")
        m2.metric("Grounding", f"{int(score.grounding_score * 100)}%", delta=None, help="Evidence grounding")
        m3.metric("Ev. Coverage", f"{int(score.evidence_coverage * 100)}%", delta=None, help="Evidence coverage")
        m4.metric("Contradictions", score.contradiction_count, delta=None, help="Number of contradictions")

        st.divider()

        # reasoning steps
        st.markdown("## 🔗 Reasoning Trace", help="Step-by-step reasoning breakdown")
        for idx, step in enumerate(trace.steps):
            emoji, bg, fg, label_class = LABEL_COLORS.get(step.audit_label, ("⚪", "#f0f0f0", "#333", "default"))
            
            st.markdown(f"""
            <div class="step-card {label_class}" style="animation-delay: {idx * 0.1}s;">
                <div style="display: flex; align-items: center; margin-bottom: 10px; gap: 8px;">
                    <span style="font-size: 1.3rem;">{emoji}</span>
                    <span class="step-label-badge" style="background-color: {bg}; color: {fg};">
                        Step {step.step_id} · {step.audit_label.upper()}
                    </span>
                    <span style="font-size: 0.85rem; color: #666; font-style: italic;">{step.label}</span>
                </div>
                <p style="margin: 12px 0 8px; color: #111; font-size: 0.95rem; line-height: 1.5;">{step.text}</p>
                <p style="font-size: 0.85rem; color: {fg}; margin: 0; font-style: italic; background: {bg}; 
                           padding: 8px 10px; border-radius: 6px; background-color: rgba(0,0,0,0.02);">
                    💬 {step.audit_explanation}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if step.citations:
                st.markdown('<div style="margin-left: 12px; margin-top: 8px;">', unsafe_allow_html=True)
                for c in step.citations:
                    st.markdown(
                        f"""<div style="animation: fadeIn 0.5s ease-out;">
                        📎 <a href="{c.url}" target="_blank" style="color: #667eea; font-weight: 500;">{c.title}</a>
                        <br><span style="font-size: 0.8rem; color: #666;">"{c.snippet[:120]}…"</span>
                        </div>"""
                    )
                st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown("## 📚 Sources Used", help="References for the reasoning")
        seen_urls = set()
        for idx, chunk in enumerate(chunks):
            if chunk.url in seen_urls:
                continue
            seen_urls.add(chunk.url)
            with st.expander(f"📄 {chunk.source[:20]}… — {chunk.title[:40]}"):
                st.markdown(f"[🔗 Open source ↗]({chunk.url})")
                st.caption(chunk.text[:400] + "…")
