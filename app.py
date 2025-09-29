import re
import io
import json
import os
from collections import Counter
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# --- Optional NLP / PDF / OCR ---
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        SPACY_AVAILABLE = False
except Exception:
    SPACY_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except Exception:
    PYPDF2_AVAILABLE = False

try:
    import pytesseract
    from pdf2image import convert_from_bytes
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# --- Keywords ---
DISEASE_KEYWORDS = ["diabetes","hypertension","covid","asthma","pneumonia",
"bronchitis","tuberculosis","cancer","malaria","coronary artery disease",
"cardiomyopathy","arthritis","stroke","hepatitis","hiv"]
SYMPTOM_KEYWORDS = ["fever","cough","shortness of breath","headache","vomiting",
"nausea","dizziness","fatigue","chest pain","abdominal pain","diarrhea",
"loss of taste","loss of smell","sore throat","weakness"]
MEDICATION_KEYWORDS = ["paracetamol","ibuprofen","metformin","insulin","amoxicillin",
"azithromycin","aspirin","atorvastatin","amlodipine","lisinopril",
"prednisone","cetirizine","azithromycin"]

DATE_PATTERN = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b"
BP_PATTERN = r"\b(?:BP[: ]*\d{2,3}/\d{2,3})\b"
HR_PATTERN = r"\b(?:HR[: ]*\d{2,3}|Heart rate[: ]*\d{2,3})\b"
DOSAGE_PATTERN = r"\b\d+(?:mg|MG|ml|mL|g|units|IU)\b"

# --- PII Patterns ---
NAME_LINE_PATTERN = r"(?im)^\s*(patient name|name)\s*[:\-]\s*.+$"
PHONE_PATTERN = r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{10}|\d{3}[-.\s]\d{3}[-.\s]\d{4})\b"
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

# --- Utility Functions ---
def deidentify_text(text):
    t = re.sub(NAME_LINE_PATTERN, "Patient Name: [REDACTED]", text)
    t = re.sub(PHONE_PATTERN, "[REDACTED_PHONE]", t)
    t = re.sub(EMAIL_PATTERN, "[REDACTED_EMAIL]", t)
    t = re.sub(r"(?im)^\s*(mrn|id|patient id|hospital id)\s*[:\-]\s*\S+\s*$",
               lambda m: m.group(0).split(":")[0] + ": [REDACTED]", t)
    return t

def keyword_search(text, keywords):
    found = set()
    lower = text.lower()
    for k in keywords:
        if k.lower() in lower:
            found.add(k)
    return sorted(found)

def find_dates(text): return sorted(set(re.findall(DATE_PATTERN, text)))
def find_bp(text): return sorted(set(re.findall(BP_PATTERN, text, flags=re.IGNORECASE)))
def find_hr(text): return sorted(set(re.findall(HR_PATTERN, text, flags=re.IGNORECASE)))

def find_medications(text):
    meds = set()
    lower = text.lower()
    for m in MEDICATION_KEYWORDS:
        if m.lower() in lower:
            meds.add(m)
    dosages = re.findall(DOSAGE_PATTERN, text)
    meds.update(dosages)
    return sorted(meds)

def extract_with_spacy(text):
    if not SPACY_AVAILABLE: return []
    doc = nlp(text)
    return [(ent.text, ent.label_) for ent in doc.ents]

def load_pdf_text_bytes(file_bytes):
    text = ""
    if PYPDF2_AVAILABLE:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for p in reader.pages:
                t = p.extract_text()
                if t: text += t + "\n"
        except: pass
    if not text.strip() and OCR_AVAILABLE:
        try:
            images = convert_from_bytes(file_bytes)
            text = "\n".join([pytesseract.image_to_string(img) for img in images])
        except: text = ""
    return text

# --- NEW: Risk Scoring ---
def generate_risk_hints(diseases, symptoms, bp, hr):
    hints = []
    if "shortness of breath" in symptoms and "fever" in symptoms:
        hints.append("⚠️ Possible Respiratory Infection — urgent review advised.")
    if "hypertension" in diseases or any("/" in b and int(b.split("/")[0].split(":")[-1]) >= 140 for b in bp):
        hints.append("⚠️ High Blood Pressure detected (Hypertension risk).")
    if any(re.search(r"\d+", h) and int(re.search(r"\d+", h).group()) > 100 for h in hr):
        hints.append("⚠️ Elevated Heart Rate (Tachycardia).")
    if "diabetes" in diseases:
        hints.append("ℹ️ Patient has Diabetes — monitor sugar levels closely.")
    if len(symptoms) >= 3:
        hints.append("⚠️ Multiple symptoms present — may require urgent triage.")
    return hints

# --- Streamlit App ---
st.set_page_config(page_title="Medical Report Analyzer", layout="wide")
st.markdown(
    """
    <style>
        .main {background-color: #f9fafc;}
        .stMetric {background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
        .risk-hint {font-size: 1.05em; margin: 5px 0; padding: 8px; border-radius: 6px;}
        .legend {display:flex;gap:10px;margin-bottom:8px;}
        .legend div{padding:6px 8px;border-radius:4px;font-size:0.9em;}
        .disease{background:#fdecea;padding:2px;border-radius:3px;}
        .symptom{background:#fff4e5;padding:2px;border-radius:3px;}
        .med{background:#e8f8f5;padding:2px;border-radius:3px;}
    </style>
    """,
    unsafe_allow_html=True
)
st.title("🩺 Advanced Medical Report Analyzer")
st.caption("Upload or paste medical records, extract structured insights, and visualize trends.")

st.sidebar.header("⚙️ Options")
input_mode = st.sidebar.radio("Input:", ["Paste Text", "Upload Files", "Sample Report", "Use Dataset"])
deid = st.sidebar.checkbox("De-identify (remove PHI)", value=True)
use_spacy = st.sidebar.checkbox("Use spaCy NER (if available)", value=SPACY_AVAILABLE)
show_raw = st.sidebar.checkbox("Show raw extracted text", value=False)

# --- Collect reports ---
report_texts = []
if input_mode == "Paste Text":
    pasted = st.text_area("📋 Paste medical report text here:", height=240)
    fname = st.text_input("Document name:", value="pasted_report.txt")
    if pasted.strip():
        report_texts.append((fname, pasted))
elif input_mode == "Upload Files":
    uploaded_files = st.file_uploader("📂 Upload reports (txt, pdf)", type=["txt","pdf"], accept_multiple_files=True)
    if uploaded_files:
        for up in uploaded_files:
            raw_bytes = up.read()
            if up.name.lower().endswith(".pdf"):
                text = load_pdf_text_bytes(raw_bytes)
            else:
                text = raw_bytes.decode("utf-8", errors="ignore")
            report_texts.append((up.name, text))
elif input_mode == "Sample Report":
    sample = (
        "Patient Name: John Doe\nAge: 57\nDate: 2025-09-15\n"
        "Chief Complaint: Patient presents with fever, cough and shortness of breath.\n"
        "History of hypertension and diabetes.\n"
        "BP: 140/90, HR: 110\n"
        "Medications: Azithromycin 500mg, Paracetamol 650mg.\n"
    )
    st.code(sample, language="text")
    report_texts.append(("sample_report.txt", sample))
elif input_mode == "Use Dataset":
    dataset_path = "data/medical_reports_100.csv"
    if os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path)
        st.subheader("📊 Dataset Overview")
        st.dataframe(df[["report_id","patient_name","age"]])
        selected_id = st.selectbox("Select Report ID:", df["report_id"])
        selected_report = df.loc[df["report_id"]==selected_id, "report_text"].values[0]
        st.text_area("Selected Report Text", value=selected_report, height=200)
        report_texts.append((f"dataset_report_{selected_id}.txt", selected_report))
    else:
        st.error("❌ Dataset not found!")

# --- Analyze Reports ---
if report_texts and st.button("🚀 Analyze Reports"):
    aggregated_results, all_dates, counts, highlighted_docs = [], [], Counter(), {}

    for fname, raw_text in report_texts:
        text = deidentify_text(raw_text) if deid else raw_text
        dates, bp, hr = find_dates(text), find_bp(text), find_hr(text)
        diseases, symptoms, meds = keyword_search(text, DISEASE_KEYWORDS), keyword_search(text, SYMPTOM_KEYWORDS), find_medications(text)
        spacy_ents = extract_with_spacy(text) if (use_spacy and SPACY_AVAILABLE) else []
        risk_hints = generate_risk_hints(diseases, symptoms, bp, hr)

        res = {"filename":fname,"dates":dates,"bp":bp,"hr":hr,"diseases":diseases,
               "symptoms":symptoms,"medications":meds,"spacy_entities":spacy_ents,
               "risk_hints":risk_hints,"raw":text}
        aggregated_results.append(res)
        all_dates.extend(dates)
        counts["diseases"] += len(diseases)
        counts["symptoms"] += len(symptoms)
        counts["medications"] += len(meds)

        # --- Highlighting ---
        esc_text = re.sub(r"&","&amp;",text); esc_text = re.sub(r"<","&lt;",esc_text); esc_text = re.sub(r">","&gt;",esc_text)
        def wrap_terms(ht, terms, css_class):
            for term in sorted(set(terms), key=lambda x:-len(x)):
                if term:
                    ht = re.sub(rf"(?i)\b({re.escape(term)})\b", rf"<span class='{css_class}'>\1</span>", ht)
            return ht
        html = wrap_terms(esc_text, diseases, "disease")
        html = wrap_terms(html, symptoms, "symptom")
        html = wrap_terms(html, meds, "med")
        html = f"<div class='legend'><div style='background:#fdecea'>Disease</div><div style='background:#fff4e5'>Symptom</div><div style='background:#e8f8f5'>Medication</div></div><pre>{html}</pre>"
        highlighted_docs[fname] = html

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["📑 Aggregated Results","📈 Visualizations","📝 Documents & Highlights"])
    with tab1:
        st.subheader("📑 Aggregated Results")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Diseases", counts["diseases"])
        col2.metric("Symptoms", counts["symptoms"])
        col3.metric("Medications", counts["medications"])
        col4.metric("Dates Found", len(all_dates))

        df_rows = [{"filename":r["filename"],"diseases":"; ".join(r["diseases"]),
                   "symptoms":"; ".join(r["symptoms"]),"medications":"; ".join(r["medications"]),
                   "dates":"; ".join(r["dates"]),"bp":"; ".join(r["bp"]),
                   "hr":"; ".join(r["hr"]),"risk_hints":"; ".join(r["risk_hints"])} for r in aggregated_results]
        st.dataframe(pd.DataFrame(df_rows),use_container_width=True)

        st.markdown("### 📥 Export Results")
        export_name = st.text_input("Export base filename:", "medical_analysis")
        st.download_button("⬇️ Download TXT", data=json.dumps(aggregated_results, indent=2), file_name=f"{export_name}.txt")
        st.download_button("⬇️ Download CSV", data=pd.DataFrame(df_rows).to_csv(index=False), file_name=f"{export_name}.csv")
        st.download_button("⬇️ Download JSON", data=json.dumps(aggregated_results, indent=2), file_name=f"{export_name}.json")

    with tab2:
        st.subheader("📈 Visualizations")
        colA, colB = st.columns(2)
        with colA:
            if all_dates:
                date_counts = Counter(all_dates)
                fig, ax = plt.subplots(figsize=(6,3))
                ax.bar(date_counts.keys(), date_counts.values(), color="#4B9CD3")
                ax.set_xticklabels(date_counts.keys(),rotation=45,ha="right")
                ax.set_title("Mentions by Date")
                st.pyplot(fig)
        with colB:
            sizes = [counts["diseases"],counts["symptoms"],counts["medications"]]
            if sum(sizes)>0:
                fig2, ax2 = plt.subplots()
                ax2.pie(sizes,labels=["Diseases","Symptoms","Medications"],autopct="%1.1f%%",startangle=90)
                ax2.axis("equal")
                st.pyplot(fig2)

    with tab3:
        st.subheader("📝 Documents & Highlights")
        for r in aggregated_results:
            st.markdown(f"### 📄 {r['filename']}")
            if r["risk_hints"]:
                for hint in r["risk_hints"]:
                    st.warning(hint)
            if show_raw:
                with st.expander("📂 Raw Text"):
                    st.text_area("Raw text", value=r["raw"], height=160)
            st.markdown(highlighted_docs[r["filename"]], unsafe_allow_html=True)

st.sidebar.success("✅ Ready for Analysis")
st.sidebar.write(f"spaCy: {SPACY_AVAILABLE} | PyPDF2: {PYPDF2_AVAILABLE} | OCR: {OCR_AVAILABLE}")
