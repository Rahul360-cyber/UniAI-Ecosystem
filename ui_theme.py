"""UI-only styling and presentation helpers for LectureLoop.

Works with Streamlit >=1.39. Does not collect, transmit, or store data.
An actual university logo is only displayed if the developer supplies an
AUTHORIZED asset at assets/polito_logo.png and opts into displaying it.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
PAGE_INFO = {
    "Student": ("Your questions deserve answers.", "Ask freely, explore ideas, and optionally help improve the next lecture.", "✦ STUDENT SPACE", "01"),
    "Practice & Reassessment": ("Learn it. Test it. Own it.", "Short concept checks reveal what to revisit—then help you measure your progress.", "✦ ADAPTIVE PRACTICE", "02"),
    "My Learning Portfolio": ("Your growth has a story.", "Document learning, experiments, and research milestones on your terms.", "✦ PRIVATE LEARNING JOURNEY", "03"),
    "Professor": ("A clearer view of your classroom.", "Turn aggregated questions into better explanations and teaching decisions.", "✦ PROFESSOR INSIGHTS", "04"),
    "Classroom Lab": ("One class. Many ways to learn.", "Organize lectures into captions, code, visuals, and accessible catch-up notes.", "✦ CLASSROOM LAB", "05"),
}

PAGE_LABELS = {
    "Student": "💬  Student AI tutor",
    "Practice & Reassessment": "🧠  Practice & reassess",
    "My Learning Portfolio": "📈  My learning portfolio",
    "Professor": "📊  Professor dashboard",
    "Classroom Lab": "🎙️  Classroom lab",
}


def _data_uri(path: Path) -> str:
    """Encode an image into a local data URI; no external image request."""
    suffix = path.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}.get(suffix)
    if not mime or not path.is_file() or path.stat().st_size > 3_000_000:
        return ""
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def logo_available() -> bool:
    return (ROOT / "assets" / "polito_logo.png").is_file()


def inject_theme(*, animated: bool = True, comfortable: bool = False, use_authorized_logo: bool = False) -> None:
    """Inject an academic-inspired theme and a subtle background watermark."""
    if use_authorized_logo and logo_available():
        watermark = _data_uri(ROOT / "assets" / "polito_logo.png")
    else:
        watermark = _data_uri(ROOT / "assets" / "torino_campus_mark.svg")
    uri_css = f'url("{watermark}")' if watermark else "none"
    animation = "none" if not animated else "ll-rise 700ms cubic-bezier(.16,1,.3,1) both"
    reading = "1.075rem" if comfortable else "1rem"
    st.markdown(f"""
<style>
:root{{--ll-navy:#092b4d;--ll-blue:#135997;--ll-sky:#22b7cb;--ll-border:#dbe9f4;--ll-muted:#4c6884}}
.stApp {{
 background:radial-gradient(circle at 95% 9%, rgba(124,209,229,.20),transparent 32%),
            radial-gradient(circle at 7% 86%, rgba(36,118,193,.08),transparent 34%),
            #f6f9fc;
}}
[data-testid="stAppViewContainer"] {{background:transparent;}}
[data-testid="stAppViewContainer"]::before{{
 content:"";position:fixed;right:2vw;bottom:2vh;width:min(34vw,460px);
 height:min(47vh,420px);background-image:{uri_css};background-repeat:no-repeat;
 background-position:center;background-size:contain;opacity:.065;
 pointer-events:none;z-index:0;
}}
[data-testid="stAppViewContainer"] > .main {{position:relative;z-index:1}}
.block-container{{padding-top:2rem;max-width:1380px;padding-bottom:4rem}}
body, [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li{{font-size:{reading}}}
header[data-testid="stHeader"]{{background:transparent}}
footer{{visibility:hidden}}
[data-testid="stSidebar"]{{background:linear-gradient(160deg,#081e36,#0b3151 63%,#10516c);border-right:1px solid #144666}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]{{color:#eff9ff}}
[data-testid="stSidebar"] h3{{color:white!important}}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] .stCaption p{{color:#dcebf5!important}}
[data-testid="stSidebar"] [role="radiogroup"] label{{border:1px solid rgba(190,230,252,.13);border-radius:13px;padding:7px 9px!important;margin:3px 0;background:rgba(255,255,255,.035);transition:background .2s,transform .2s}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{{background:rgba(128,215,239,.13);transform:translateX(3px)}}
[data-testid="stSidebar"] [role="radiogroup"] label p{{color:#f3fbff!important;font-size:.91rem}}
[data-testid="stSidebar"] hr{{border-color:rgba(198,231,244,.18)}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input{{background:#f2f8fc!important;color:#0c2d48!important}}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"]{{
 color:#fff!important;background:linear-gradient(110deg,#0b558e,#087ea7)!important;
 border:0!important;box-shadow:0 8px 22px rgba(9,85,143,.17);
}}
.stButton button, .stFormSubmitButton button, .stDownloadButton button{{border-radius:12px!important;transition:transform .15s ease,box-shadow .15s ease}}
.stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(18,75,114,.13)}}
[data-testid="stMetric"]{{background:linear-gradient(145deg,rgba(255,255,255,.96),rgba(232,244,251,.95));border:1px solid #deebf4;border-radius:17px;padding:15px 19px;box-shadow:0 6px 19px rgba(23,81,124,.045)}}
[data-testid="stMetricValue"]{{color:#0b4775}}
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"]{{border-radius:15px;overflow:hidden}}
[data-testid="stExpander"]{{border:1px solid #dbeaf4!important;border-radius:15px!important;background:rgba(255,255,255,.66)}}
[data-testid="stForm"]{{border:1px solid #d9e8f2!important;border-radius:18px!important;background:rgba(255,255,255,.72);padding:20px}}
button[data-baseweb="tab"]{{border-radius:10px 10px 0 0;padding-left:17px;padding-right:17px}}
button[data-baseweb="tab"]:hover{{background:rgba(14,113,173,.06)}}
.ll-brand{{display:flex;align-items:center;gap:12px;padding:8px 0 15px}}
.ll-mark{{display:grid;place-items:center;height:43px;width:43px;border-radius:14px;background:linear-gradient(145deg,#35c9e0,#1466b0);font-size:22px;color:#fff;box-shadow:0 8px 25px rgba(11,161,211,.3)}}
.ll-brand strong{{display:block;color:#fff;font-size:1.18rem;letter-spacing:-.03em}}
.ll-brand small{{display:block;color:#a4d4ea;font-size:.76rem}}
.ll-overline{{color:#6bc9e1;font-size:.72rem;letter-spacing:.13em;font-weight:800}}
.ll-hero{{position:relative;overflow:hidden;border:1px solid rgba(168,210,232,.85);border-radius:24px;
 background:linear-gradient(115deg,#ffffff 5%,#edf7fd 61%,#ddf1fa 100%);
 box-shadow:0 15px 35px rgba(10,61,105,.07);padding:28px 33px 27px;margin-bottom:20px;
 animation:{animation};}}
.ll-hero::after{{content:"";position:absolute;right:-50px;top:-91px;width:300px;height:300px;
 border:1px solid rgba(29,130,191,.12);border-radius:50%;box-shadow:0 0 0 43px rgba(40,136,185,.045),0 0 0 100px rgba(40,136,185,.035);pointer-events:none}}
.ll-hero h1{{font-size:clamp(1.7rem,3.1vw,2.8rem);color:#0b3259!important;font-weight:800;letter-spacing:-.045em;line-height:1.1;margin:10px 0!important;max-width:850px}}
.ll-hero p{{color:#42627c!important;font-size:1.02rem;max-width:780px;margin:0 0 14px!important}}
.ll-chipline{{display:flex;flex-wrap:wrap;gap:9px;align-items:center}}
.ll-chip{{display:inline-flex;align-items:center;border-radius:25px;border:1px solid #cadeeb;background:rgba(255,255,255,.8);padding:6px 12px;color:#325a7d;font-size:.77rem;font-weight:700}}
.ll-chip-active{{border-color:#95d9c6;background:#e2f7ec;color:#107156}}
.ll-guide{{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 18px}}
.ll-guide-step{{flex:1 1 160px;border:1px solid #d7e7f2;background:#fff;border-radius:14px;padding:13px 15px;box-shadow:0 5px 16px rgba(14,62,97,.04)}}
.ll-guide-step b{{display:block;color:#0b4c7a;font-size:.82rem;letter-spacing:.02em}}
.ll-guide-step span{{display:block;color:#53708a;font-size:.84rem;line-height:1.4;margin-top:4px}}
.ll-guide-step.ll-current{{border-color:#50b9d2;background:#eaf8fb}}
.ll-section-note{{border-left:4px solid #20a1bf;background:rgba(228,245,252,.82);border-radius:0 12px 12px 0;padding:13px 17px;margin:12px 0 17px;color:#315675}}
.ll-footer{{font-size:.77rem;color:#537189;padding-top:12px;border-top:1px solid #dae7ee}}
@keyframes ll-rise{{from{{transform:translateY(9px);opacity:.5}}to{{transform:translateY(0);opacity:1}}}}
@media (max-width:700px){{.ll-hero{{padding:21px 18px}}.ll-hero::after{{width:140px;height:140px;top:-20px;right:-80px}}.block-container{{padding-top:1rem}}}}
@media (prefers-reduced-motion:reduce){{.ll-hero, .stButton button, [data-testid="stSidebar"] [role="radiogroup"] label{{animation:none!important;transition:none!important}}}}
</style>""", unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.markdown('''<div class="ll-brand"><div class="ll-mark">↗</div>
<div><strong>LectureLoop</strong><small>Learning, connected.</small></div></div>''', unsafe_allow_html=True)
    st.markdown('<div class="ll-overline">YOUR LEARNING SPACE</div>', unsafe_allow_html=True)


def render_hero(page: str, class_code: str, *, ai_enabled: bool = False, private_portfolio: bool = False) -> None:
    heading, subtitle, overline, _ = PAGE_INFO.get(page, PAGE_INFO["Student"])
    chips = [f"<span class='ll-chip'>CLASS {html.escape(class_code)}</span>",
             f"<span class='ll-chip {'ll-chip-active' if ai_enabled else ''}'>{'● Gemini enabled' if ai_enabled else '○ Offline demo'}</span>"]
    if private_portfolio:
        chips.append("<span class='ll-chip ll-chip-active'>◉ Private portfolio unlocked</span>")
    st.markdown(f'''<section class="ll-hero" aria-label="Current workspace">
      <div class="ll-overline">{html.escape(overline)}</div>
      <h1>{html.escape(heading)}</h1><p>{html.escape(subtitle)}</p>
      <div class="ll-chipline">{''.join(chips)}</div>
    </section>''', unsafe_allow_html=True)


def render_guide(stage: int) -> None:
    steps = [("01 · ASK", "Explore what wasn't clear"),
             ("02 · PRACTICE", "Check and strengthen understanding"),
             ("03 · DOCUMENT", "Own your learning evidence"),
             ("04 · IMPROVE", "Support better teaching")]
    blocks = ''.join(
        f'<div class="ll-guide-step {"ll-current" if idx==stage else ""}"><b>{html.escape(heading)}</b>'
        f'<span>{html.escape(subtitle)}</span></div>'
        for idx, (heading, subtitle) in enumerate(steps, start=1)
    )
    st.markdown(f'<div class="ll-guide">{blocks}</div>', unsafe_allow_html=True)


def render_note(message: str) -> None:
    st.markdown(f'<div class="ll-section-note">{html.escape(message)}</div>', unsafe_allow_html=True)


def show_footer() -> None:
    st.markdown('<div class="ll-footer">Independent student hackathon prototype · Not an official Politecnico di Torino service.</div>', unsafe_allow_html=True)
