"""Self-contained UI. No user preferences are stored in the database."""
import base64
from pathlib import Path
import streamlit as st


def inject_theme(focus_mode=False, large_text=False, reduced_motion=False, authorized_logo=False):
    root = Path(__file__).resolve().parent
    img = root / 'assets' / ('polito_logo.png' if authorized_logo and (root/'assets'/'polito_logo.png').is_file() else 'torino_campus_mark.svg')
    if img.is_file():
        mime = 'image/png' if img.suffix.lower() == '.png' else 'image/svg+xml'
        uri = f'data:{mime};base64,' + base64.b64encode(img.read_bytes()).decode('ascii')
        bg = f'url("{uri}")'
    else:
        bg = 'none'
    size = '1.13rem' if large_text else '1rem'
    anim = 'none!important' if reduced_motion else 'inherit'
    st.markdown(f'''<style>
    .stApp {{background: radial-gradient(circle at top right, #dcf1fa 0%, transparent 34%),#f7fafc;}}
    [data-testid="stAppViewContainer"]::before{{content:"";position:fixed;right:2%;bottom:1%;width:32vw;height:36vh;background-image:{bg};background-position:center;background-size:contain;background-repeat:no-repeat;opacity:.055;pointer-events:none;}}
    .main .block-container{{max-width:1340px;padding-top:1.7rem;padding-bottom:4rem;position:relative;}}
    [data-testid="stSidebar"]{{background:linear-gradient(160deg,#09243f,#123f63);}}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,[data-testid="stSidebar"] label{{color:#e4f4ff!important;}}
    h1,h2,h3{{color:#123c63!important;letter-spacing:-.025em;}}
    [data-testid="stMetric"]{{background:white;border:1px solid #d6e8f3;border-radius:16px;padding:16px;}}
    [data-testid="stForm"]{{border-radius:17px;border:1px solid #d5e7f3;background:rgba(255,255,255,.7);}}
    .stButton button,.stDownloadButton button{{border-radius:12px;}}
    .stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{{background:#0967a1!important;border:none!important;color:white!important;}}
    [data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{{font-size:{size};}}
    .ClassPair-banner{{background:linear-gradient(120deg,#0d4169,#0a788b);border-radius:20px;padding:25px;color:#fff!important;margin-bottom:16px;}}
    .ClassPair-banner h1,.ClassPair-banner p{{color:white!important;}}
    .ClassPair-banner p{{opacity:.88;}}
    .ClassPair-chip{{padding:5px 10px;border-radius:50px;border:1px solid #b8e6ed;background:#e8f8fc;color:#145773;font-weight:600;font-size:.82rem;}}
    {'[data-testid="stMarkdownContainer"] li{line-height:1.8;}' if focus_mode else ''}
    *{{animation:{anim};}}
    </style>''', unsafe_allow_html=True)


def banner(role, course):
    # Escape text to avoid reflecting user-managed course strings into HTML.
    import html
    st.markdown('<div class="ClassPair-banner"><h1>ClassPair · '+html.escape(role)+''' Portal</h1>
        <p>Learn together. Understand better. · '''+html.escape(course)+'''</p></div>''',unsafe_allow_html=True)
