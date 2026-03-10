import streamlit as st
import requests
from groq import Groq
from fpdf import FPDF
import re

# ── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Interview Intel Agent",
    page_icon="🎙️",
    layout="wide",
)

# ── Premium Dark UI ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #0a0a0f;
    color: #e8e6f0;
}

.big-title {
    font-family: 'Syne', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #e8e6f0 0%, #a78bfa 60%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}

.subtitle {
    color: #6b7280;
    margin-bottom: 2rem;
}

.stTextInput input, .stTextArea textarea {
    background: #13131a !important;
    border: 1px solid #1f1f2e !important;
    color: white !important;
}

.stSelectbox div[data-baseweb="select"] {
    background: #13131a !important;
}

.stButton button {
    background: linear-gradient(135deg, #7c3aed, #db2777);
    color: white;
    border-radius: 12px;
    font-weight: 700;
    padding: 0.6rem 2rem;
    border: none;
}

.stButton button:hover {
    opacity: 0.85;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🎙️ Interview Intel Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Wikipedia-powered interview research. Clean. Reliable. Focused.</div>', unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 Groq API Key")
    st.markdown("Get your free key at [console.groq.com](https://console.groq.com)")
    groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")

    st.markdown("---")
    st.markdown("### 🤖 Model")
    model_choice = st.selectbox("Choose Model", [
        "llama-3.3-70b-versatile",
        "llama3-70b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ])

# ── Main Layout ─────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    guest_name = st.text_input("Guest Name", placeholder="e.g. Elon Musk")

with col2:
    interview_type = st.selectbox("Interview Type", [
        "Podcast / Long-form",
        "Job Interview",
        "Journalism / News",
        "Research / Academic"
    ])

context = st.text_area("Additional Context (optional)", height=80)
intensity = st.slider("Question Intensity", 1, 5, 3)
run_btn = st.button("🚀 Research & Generate Questions", use_container_width=True)

# ── Wikipedia Research ───────────────────────────────────
def research_guest_wikipedia(name: str):
    search_url = "https://en.wikipedia.org/w/api.php"

    try:
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": name,
            "format": "json"
        }
        search_response = requests.get(
            search_url, params=search_params, timeout=10,
            headers={"User-Agent": "InterviewIntelAgent/1.0"}
        )
        if search_response.status_code != 200:
            return None

        search_json = search_response.json()
        if not search_json.get("query", {}).get("search"):
            return None

        page_title = search_json["query"]["search"][0]["title"]

        page_params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": True,
            "titles": page_title,
            "format": "json"
        }
        page_response = requests.get(
            search_url, params=page_params, timeout=10,
            headers={"User-Agent": "InterviewIntelAgent/1.0"}
        )
        if page_response.status_code != 200:
            return None

        page_json = page_response.json()
        pages = page_json.get("query", {}).get("pages", {})
        page_content = next(iter(pages.values())).get("extract", "")

        if not page_content:
            return None

        return {"title": page_title, "content": page_content[:7000]}

    except (requests.exceptions.RequestException, ValueError):
        return None

# ── Groq API Call ────────────────────────────────────────
def safe_generate(prompt: str, api_key: str, model: str) -> str:
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "Invalid Groq API key. Keys start with 'gsk_'. "
            "Get yours free at https://console.groq.com"
        )

    client = Groq(api_key="api_key_here")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.7,
    )
    return response.choices[0].message.content

# ── Prompt Builder ───────────────────────────────────────
def build_prompt(name, interview_type, context, wiki_data, intensity):
    return f"""
You are an elite pre-interview strategist.

ONLY use the following Wikipedia content.
If something is not present, say "Not available in Wikipedia."

Guest: {name}
Interview Type: {interview_type}
Tone Intensity: {intensity}/5
Additional Context: {context or "None"}

WIKIPEDIA CONTENT:
{wiki_data['content']}

Produce:

## GUEST INTELLIGENCE BRIEF
- Who they are
- Career highlights
- Major milestones
- Public positions
- Controversies (only if mentioned)
- Unique angles

---

## QUESTION BANK

### Warm-Up (3)
### Deep-Dive (5)
### Challenge (3)
### Follow-ups (3)

---

## QUESTIONS NOT TO ASK
"""

# ── PDF Generator ────────────────────────────────────────
def generate_pdf(name, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    safe_name = name.encode("latin-1", "replace").decode("latin-1")
    pdf.cell(0, 10, f"Interview Brief: {safe_name}", ln=True)
    pdf.ln(4)

    # Body
    pdf.set_font("Helvetica", "", 10)

    # Strip non-latin characters completely
    clean = re.sub(r"[#*`]", "", content)
    clean = re.sub(r"[^\x20-\x7E\n]", "", clean)  # only printable ASCII

    for line in clean.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(3)
        else:
            try:
                pdf.multi_cell(170, 5, line)
            except Exception:
                pass  # skip any line that still fails

    return bytes(pdf.output(dest="S"))

# ── Run Agent ───────────────────────────────────────────
if run_btn:

    if not groq_key:
        st.error("⚠️ Please enter your Groq API key in the sidebar.")
        st.stop()

    if not guest_name:
        st.error("⚠️ Please enter a guest name.")
        st.stop()

    try:
        with st.spinner("🔍 Fetching Wikipedia data..."):
            wiki_data = research_guest_wikipedia(guest_name)

        if not wiki_data:
            st.error("No Wikipedia page found for that name.")
            st.stop()

        with st.spinner(f"🧠 Generating intelligence brief with {model_choice}..."):
            prompt = build_prompt(guest_name, interview_type, context, wiki_data, intensity)
            output = safe_generate(prompt, groq_key, model_choice)

        with st.spinner("📄 Preparing PDF..."):
            pdf_bytes = generate_pdf(guest_name, output)

        st.success("✅ Done!")
        st.markdown(output)

        st.download_button(
            "⬇️ Download PDF",
            pdf_bytes,
            file_name=f"{guest_name.replace(' ', '_')}_brief.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    except ValueError as e:
        st.error(f"⚠️ {e}")
    except Exception as e:
        st.error(f"⚠️ {e}")
