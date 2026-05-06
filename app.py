"""
app.py  —  COT-Trace Streamlit UI
Run: streamlit run app.py
"""
import os
import streamlit as st
from anthropic import Anthropic, RateLimitError
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
    initial_sidebar_state="expanded",
)

# Hide code display
st.markdown("""
<style>
    [data-testid="stMarkdownContainer"] code {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

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
    
    @keyframes floatUp {
        0% {
            opacity: 0;
            transform: translateY(40px);
        }
        50% {
            opacity: 1;
        }
        100% {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes rotate360 {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    @keyframes scaleInOut {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    @keyframes gradientBorder {
        0% {
            border-color: #667eea;
            box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
        }
        50% {
            border-color: #764ba2;
            box-shadow: 0 0 20px rgba(118, 75, 162, 0.5);
        }
        100% {
            border-color: #667eea;
            box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
        }
    }
    
    @keyframes waveAnimation {
        0%, 100% { opacity: 0.5; transform: translateY(0); }
        50% { opacity: 1; transform: translateY(-5px); }
    }
    
    @keyframes rainbowBg {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* ─── Advanced Blob Animations ─── */
    @keyframes blob1 {
        0%, 100% {
            transform: translate(0, 0) scale(1);
            opacity: 0.7;
        }
        25% {
            transform: translate(50px, -80px) scale(1.1);
            opacity: 0.6;
        }
        50% {
            transform: translate(-30px, 100px) scale(0.9);
            opacity: 0.8;
        }
        75% {
            transform: translate(-80px, -50px) scale(1.05);
            opacity: 0.65;
        }
    }
    
    @keyframes blob2 {
        0%, 100% {
            transform: translate(0, 0) scale(1);
            opacity: 0.6;
        }
        33% {
            transform: translate(-60px, 80px) scale(1.15);
            opacity: 0.7;
        }
        66% {
            transform: translate(100px, -60px) scale(0.95);
            opacity: 0.55;
        }
    }
    
    @keyframes blob3 {
        0%, 100% {
            transform: translate(0, 0) scale(1);
            opacity: 0.5;
        }
        25% {
            transform: translate(80px, 60px) scale(1.08);
            opacity: 0.65;
        }
        50% {
            transform: translate(-70px, -90px) scale(0.92);
            opacity: 0.6;
        }
        75% {
            transform: translate(40px, 70px) scale(1.02);
            opacity: 0.7;
        }
    }
    
    @keyframes float-particle {
        0% {
            transform: translateY(0) translateX(0) rotate(0deg);
            opacity: 0;
        }
        10% {
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        100% {
            transform: translateY(-100vh) translateX(50px) rotate(360deg);
            opacity: 0;
        }
    }
    
    @keyframes sway {
        0%, 100% { transform: translateX(0); }
        50% { transform: translateX(20px); }
    }
    
    @keyframes wave-motion {
        0%, 100% { transform: translateY(0) translateX(0); }
        25% { transform: translateY(-15px) translateX(10px); }
        50% { transform: translateY(0) translateX(20px); }
        75% { transform: translateY(15px) translateX(10px); }
    }
    
    @keyframes luminous-pulse {
        0%, 100% {
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3),
                        inset 0 0 20px rgba(102, 126, 234, 0.1);
        }
        50% {
            box-shadow: 0 0 40px rgba(118, 75, 162, 0.5),
                        inset 0 0 30px rgba(118, 75, 162, 0.2);
        }
    }
    
    /* ─── Main Container Styling ─── */
    .main {
        animation: fadeIn 0.8s ease-in-out;
    }
    
    /* ─── Header & Title Styling ─── */
    h1 {
        animation: fadeInUp 0.6s ease-out, luminous-pulse 4s ease-in-out 0.6s infinite;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #667eea 100%);
        background-size: 200% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        letter-spacing: -1px;
        text-shadow: 0 0 30px rgba(102, 126, 234, 0.3);
    }
    
    h2 {
        animation: slideInRight 0.5s ease-out;
        border-left: 4px solid #667eea;
        padding-left: 12px;
        transition: all 0.3s ease;
        color: #fff;
    }
    
    h2:hover {
        border-left-color: #764ba2;
        padding-left: 16px;
        color: #a0b8ff;
    }
    
    h3 {
        color: #fff;
        text-shadow: 0 0 20px rgba(102, 126, 234, 0.2);
    }
    
    /* ─── Input Field Styling ─── */
    .stTextInput input {
        animation: fadeIn 0.6s ease-out 0.1s both;
        border: 2px solid transparent !important;
        border-radius: 12px !important;
        background: linear-gradient(rgba(255,255,255,0.95), rgba(255,255,255,0.95)) padding-box, linear-gradient(135deg, #667eea, #764ba2) border-box !important;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        color: #111 !important;
    }
    
    .stTextInput input:focus {
        box-shadow: 0 8px 35px rgba(102, 126, 234, 0.5) !important;
        transform: translateY(-2px);
    }
    
    .stTextInput input::placeholder {
        color: #999 !important;
    }
    
    /* ─── General Text Styling ─── */
    p, span, li, div {
        color: #e0e0e0;
    }
    
    .stMarkdown, .stMarkdown p {
        color: #e0e0e0 !important;
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
        background: linear-gradient(180deg, #1a1a3e 0%, #2d1b4e 50%, #1a1a3e 100%);
        animation: slideInLeft 0.5s ease-out;
        backdrop-filter: blur(10px);
    }
    
    [data-testid="stSidebar"] h1 {
        animation: bounceIn 0.7s ease-out;
        color: #fff;
    }
    
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: #b0b0d0;
    }
    
    [data-testid="stSidebar"] .stCaption {
        color: #9090b0;
    }
    
    /* ─── Metric Cards ─── */
    [data-testid="metric-container"] {
        animation: fadeInUp 0.6s ease-out both, luminous-pulse 4s ease-in-out 0.8s infinite;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.1) 100%);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 12px;
        padding: 16px;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
        backdrop-filter: blur(10px);
    }
    
    [data-testid="metric-container"]:hover {
        border-color: rgba(102, 126, 234, 0.6);
        box-shadow: 0 8px 35px rgba(102, 126, 234, 0.4);
        transform: translateY(-4px) scale(1.02);
    }
    
    [data-testid="metric-container"] p {
        color: #e0e0e0;
    }
    
    [data-testid="metric-container"] div {
        color: #fff;
    }
    
    /* ─── Container Styling ─── */
    .stContainer {
        animation: slideUp 0.5s ease-out;
    }
    
    /* ─── Expander Styling ─── */
    [data-testid="stExpander"] {
        animation: fadeIn 0.5s ease-out;
        border: 2px solid rgba(102, 126, 234, 0.2) !important;
        border-radius: 12px !important;
        transition: all 0.3s ease;
        background: rgba(20, 20, 50, 0.4) !important;
        backdrop-filter: blur(10px);
    }
    
    [data-testid="stExpander"]:hover {
        border-color: rgba(102, 126, 234, 0.5) !important;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
    }
    
    [data-testid="stExpander"] p, [data-testid="stExpander"] span {
        color: #e0e0e0;
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
        background: rgba(50, 30, 50, 0.6) !important;
        backdrop-filter: blur(10px);
    }
    
    [data-testid="stWarning"]:hover, [data-testid="stError"]:hover, [data-testid="stSuccess"]:hover {
        transform: translateX(4px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
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
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
    }
    
    .step-card:before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        animation: shimmer 3s infinite;
    }
    
    .step-card:hover {
        transform: translateX(6px) translateY(-4px);
        box-shadow: 0 16px 40px rgba(102, 126, 234, 0.4);
    }
    
    .step-card.supported {
        border-color: #10b981;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.08) 100%);
    }
    
    .step-card.weak {
        border-color: #f59e0b;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.08) 100%);
    }
    
    .step-card.unsupported, .step-card.contradictory {
        border-color: #ef4444;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.08) 100%);
    }
    
    .step-card.speculative {
        border-color: #f97316;
        background: linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(249, 115, 22, 0.08) 100%);
    }
    
    .step-card p, .step-card span {
        color: #e0e0e0;
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
    
    /* ─── Advanced Floating Elements ─── */
    .floating-element {
        animation: floatUp 0.8s ease-out, pulse 3s ease-in-out 0.8s infinite;
    }
    
    /* ─── Gradient Text Animation ─── */
    .gradient-text {
        background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
        background-size: 200% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: rainbowBg 4s ease infinite;
    }
    
    /* ─── Title Animation with Icon ─── */
    .title-icon {
        display: inline-block;
        animation: rotate360 20s linear infinite;
        margin-right: 12px;
    }
    
    /* ─── Glowing Border Cards ─── */
    .glow-card {
        border: 2px solid transparent;
        border-radius: 12px;
        padding: 20px;
        background: linear-gradient(rgba(20, 20, 50, 0.6), rgba(20, 20, 50, 0.6)) padding-box, linear-gradient(135deg, #667eea, #764ba2) border-box;
        animation: gradientBorder 3s ease infinite;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
    }
    
    .glow-card:hover {
        transform: translateY(-8px) scale(1.01);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.3);
    }
    
    .glow-card p {
        color: #e0e0e0;
    }
    
    /* ─── Wave Animation ─── */
    .wave-item {
        display: inline-block;
        animation: waveAnimation 0.6s ease-in-out;
    }
    
    .wave-item:nth-child(1) { animation-delay: 0s; }
    .wave-item:nth-child(2) { animation-delay: 0.1s; }
    .wave-item:nth-child(3) { animation-delay: 0.2s; }
    .wave-item:nth-child(4) { animation-delay: 0.3s; }
    .wave-item:nth-child(5) { animation-delay: 0.4s; }
    
    /* ─── Advanced Hover Effects ─── */
    .interactive-element {
        transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        position: relative;
    }
    
    .interactive-element:hover {
        transform: translateY(-6px);
        filter: drop-shadow(0 10px 25px rgba(102, 126, 234, 0.3));
    }
    
    /* ─── Pulse Glow ─── */
    .pulse-glow {
        animation: pulse 2s ease-in-out infinite, glow 2s ease-in-out infinite;
    }
    
    /* ─── Slide & Fade Combined ─── */
    .slide-fade {
        animation: slideInRight 0.6s ease-out, fadeIn 0.6s ease-out;
    }
    
    /* ─── Bounce Enter ─── */
    .bounce-enter {
        animation: bounceIn 0.7s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    }
    
    /* ─── Page Background Animation ─── */
    body, .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 25%, #2d1b4e 50%, #1a1a3e 75%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientShift 20s ease infinite;
        position: relative;
        overflow: hidden;
    }
    
    /* ─── Background Overlay Layers ─── */
    body::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(circle at 20% 50%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 40% 0%, rgba(100, 200, 255, 0.1) 0%, transparent 60%);
        animation: sway 20s ease-in-out infinite;
        z-index: 0;
        pointer-events: none;
    }
    
    /* ─── Floating Blobs Background ─── */
    body::after {
        content: '';
        position: fixed;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: 
            radial-gradient(ellipse 400px 600px at 20% 30%, rgba(102, 126, 234, 0.08) 0%, transparent 40%),
            radial-gradient(ellipse 600px 400px at 80% 60%, rgba(118, 75, 162, 0.08) 0%, transparent 40%),
            radial-gradient(ellipse 500px 500px at 50% 80%, rgba(100, 200, 255, 0.06) 0%, transparent 50%);
        animation: wave-motion 25s ease-in-out infinite;
        z-index: 1;
        pointer-events: none;
    }
    
    /* ─── Blob Elements ─── */
    .stApp::before {
        content: '';
        position: fixed;
        bottom: -200px;
        left: -200px;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, rgba(102, 126, 234, 0.1) 0%, transparent 70%);
        border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%;
        animation: blob1 25s infinite ease-in-out;
        z-index: 0;
        pointer-events: none;
        mix-blend-mode: screen;
    }
    
    .stApp::after {
        content: '';
        position: fixed;
        top: -150px;
        right: -100px;
        width: 600px;
        height: 600px;
        background: radial-gradient(circle, rgba(118, 75, 162, 0.08) 0%, transparent 70%);
        border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%;
        animation: blob2 30s infinite ease-in-out;
        z-index: 0;
        pointer-events: none;
        mix-blend-mode: screen;
    }
    
    /* ─── Third Blob ─── */
    [data-testid="stAppViewContainer"]::before {
        content: '';
        position: fixed;
        bottom: 200px;
        right: -300px;
        width: 700px;
        height: 700px;
        background: radial-gradient(circle, rgba(100, 200, 255, 0.08) 0%, transparent 70%);
        border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
        animation: blob3 35s infinite ease-in-out;
        z-index: 0;
        pointer-events: none;
        mix-blend-mode: screen;
    }
    
    /* ─── Main Content Container ─── */
    [data-testid="stAppViewContainer"] {
        position: relative;
        z-index: 10;
    }
    
    /* ─── Smooth Scroll ─── */
    html {
        scroll-behavior: smooth;
    }
    
    /* ─── Backdrop Effects ─── */
    [data-testid="stMainBlockContainer"] {
        backdrop-filter: blur(0.5px);
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
    st.markdown("### <span class='title-icon'>⚙️</span>COT-Trace", unsafe_allow_html=True, help="Live web reasoning auditor")
    st.caption("🔍 Live web reasoning auditor")
    st.divider()

    # Load tokens from environment variables (hidden from UI)
    apify_token = os.getenv("APIFY_TOKEN", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

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
<div style="text-align: center; margin-bottom: 40px; animation: floatUp 0.8s ease-out;">
    <h1 class="gradient-text" style="margin-bottom: 10px; font-size: 3rem; letter-spacing: -2px;">
        🔍 COT-Trace
    </h1>
    <p style="font-size: 1.15rem; color: #555; font-weight: 500; animation: fadeIn 0.8s ease-out 0.2s both; 
               background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.05) 100%);
               padding: 20px 30px; border-radius: 12px; backdrop-filter: blur(10px);">
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
    run_btn = st.button("Audit 🚀", type="primary", disabled=not question, use_container_width=True, help="Start the audit")

if run_btn:
    if "retriever" not in st.session_state:
        st.error("🚨 Load sources first (sidebar).")
        st.stop()
    if not anthropic_key:
        st.error("🚨 Anthropic API key required.")
        st.stop()

    client = Anthropic(api_key=anthropic_key)
    retriever: Retriever = st.session_state["retriever"]

    with st.spinner("🔎 Retrieving relevant evidence…"):
        chunks = retriever.query(question)

    if not chunks:
        st.warning("⚠️ No relevant chunks found. Try a different question or reload sources.")
        st.stop()

    try:
        with st.spinner("🧠 Generating reasoning trace…"):
            trace = generate_trace(client, question, chunks)
    except RateLimitError:
        st.error("⚠️ Rate limit reached. Please wait a few seconds and try again.")
        st.stop()
    except Exception:
        st.error("⚠️ Failed to generate the reasoning trace. Check your API usage or logs.")
        st.stop()

    try:
        with st.spinner("✅ Auditing each reasoning step…"):
            trace, score = audit_trace(client, trace, chunks)
    except RateLimitError:
        st.error("⚠️ Rate limit reached during audit. Please wait a few seconds and retry.")
        st.stop()
    except Exception:
        st.error("⚠️ Failed to audit the reasoning trace. Check your API usage or logs.")
        st.stop()

    # ── layout ───────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        # answer section
        st.markdown("## 💡 Answer", help="The model's answer to your question")
        st.markdown(f"""
        <div class="glow-card interactive-element slide-fade" style="
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.05) 100%);
            border-left: 5px solid #667eea;
        ">
            <p style="font-size: 1.05rem; color: #111; line-height: 1.6; margin: 0;">{trace.answer}</p>
        </div>
        """, unsafe_allow_html=True)

        conf_pct = int(trace.confidence * 100)
        col_conf, col_empty = st.columns([0.3, 0.7])
        with col_conf:
            st.markdown(f"""
            <div class="pulse-glow" style="padding: 16px; border-radius: 10px; 
                background: linear-gradient(135deg, #f0f3ff 0%, #fff 100%); text-align: center;">
                <p style="margin: 0; font-size: 0.85rem; color: #667eea; font-weight: 600;">📊 CONFIDENCE</p>
                <p style="margin: 8px 0 0; font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #667eea, #764ba2);
                          -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                    {conf_pct}%
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        if trace.risk_flags and trace.risk_flags != ["none"]:
            st.markdown(f"""
            <div class="bounce-enter" style="
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
        
        with m1:
            st.markdown("""
            <div class="floating-element" style="animation-delay: 0.1s;">
            """, unsafe_allow_html=True)
            st.metric("Overall", f"{int(score.overall * 100)}%", delta=None, help="Overall audit score")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with m2:
            st.markdown("""
            <div class="floating-element" style="animation-delay: 0.2s;">
            """, unsafe_allow_html=True)
            st.metric("Grounding", f"{int(score.grounding_score * 100)}%", delta=None, help="Evidence grounding")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with m3:
            st.markdown("""
            <div class="floating-element" style="animation-delay: 0.3s;">
            """, unsafe_allow_html=True)
            st.metric("Ev. Coverage", f"{int(score.evidence_coverage * 100)}%", delta=None, help="Evidence coverage")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with m4:
            st.markdown("""
            <div class="floating-element" style="animation-delay: 0.4s;">
            """, unsafe_allow_html=True)
            st.metric("Contradictions", score.contradiction_count, delta=None, help="Number of contradictions")
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # reasoning steps
        st.markdown("## 🔗 Reasoning Trace", help="Step-by-step reasoning breakdown")
        for idx, step in enumerate(trace.steps):
            emoji, bg, fg, label_class = LABEL_COLORS.get(step.audit_label, ("⚪", "#f0f0f0", "#333", "default"))
            
            st.markdown(f"""
            <div class="step-card {label_class} interactive-element" style="animation-delay: {idx * 0.1}s;">
                <div style="display: flex; align-items: center; margin-bottom: 10px; gap: 8px;">
                    <span style="font-size: 1.3rem; animation: bounceIn 0.7s ease-out {0.5 + idx*0.1}s both;">{emoji}</span>
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
                        f"""<div class="slide-fade" style="animation-delay: {idx*0.1 + 0.3}s;">
                        📎 <a href="{c.url}" target="_blank" style="color: #667eea; font-weight: 500; transition: all 0.3s ease;">
                            {c.title}
                        </a>
                        <br><span style="font-size: 0.8rem; color: #666;">"{c.snippet[:120]}…"</span>
                        </div>""",
                        unsafe_allow_html=True
                    )
                st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown("## 📚 Sources Used", help="References for the reasoning")
        seen_urls = set()
        for idx, chunk in enumerate(chunks):
            if chunk.url in seen_urls:
                continue
            seen_urls.add(chunk.url)
            
            st.markdown(f"""
            <div class="floating-element" style="animation-delay: {idx*0.15}s; margin-bottom: 10px;">
            """, unsafe_allow_html=True)
            
            with st.expander(f"📄 {chunk.source[:20]}… — {chunk.title[:40]}", expanded=False):
                st.markdown(f"<a href='{chunk.url}' target='_blank' style='color: #667eea; font-weight: 600; text-decoration: none;'>[🔗 Open source ↗]</a>", unsafe_allow_html=True)
                st.caption(chunk.text[:400] + "…")
            
            st.markdown("</div>", unsafe_allow_html=True)
