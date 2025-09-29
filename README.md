# Medical Report Analyzer

##  Project Overview

Medical reports contain critical patient information such as symptoms, diagnoses, medications, vitals, and dates. Manually reviewing them is often time-consuming and prone to errors.  

The **Advanced Medical Report Analyzer** is an interactive **Streamlit application** designed to automatically extract, organize, highlight, and visualize important medical information from **text and PDF reports**.  

It supports **multi-file analysis**, works with **datasets**, provides **visual summaries**, and allows exporting results in multiple formats.  

This tool is ideal for:  
- Students and researchers exploring **healthcare NLP projects**  
- Healthcare professionals looking for **quick report parsing**  
- Developers interested in **medical text analysis and visualization**

---

## Features

### Input Options
- Paste text reports directly
- Upload multiple `.txt` or `.pdf` files
- Load a sample report for testing

### Information Extraction
- **Diseases** (e.g., Diabetes, Hypertension, Pneumonia)
- **Symptoms** (e.g., Fever, Cough, Fatigue)
- **Medications** (with dosages, e.g., Paracetamol 650mg)
- **Vital Signs:** Blood Pressure, Heart Rate
- **Dates:** Report dates, visit dates, or examination dates

### Advanced NLP (Optional)
- Uses **spaCy NER** to extract entities like names, dates, and medical terms
- Can highlight extracted entities directly in the report text

### OCR Support (Optional)
- Extract text from scanned PDF reports using **pytesseract + pdf2image**
- Automatically falls back to OCR if PDF text extraction fails

### Data Visualization
- **Pie chart:** Distribution of diseases, symptoms, and medications
- **Bar chart:** Timeline of extracted dates (frequency per date)
- Works for both single reports and dataset aggregation

### Report Highlighting
- Diseases:  highlighted in red
- Symptoms:  highlighted in orange
- Medications:  highlighted in green
- Uses HTML/CSS for color-coded highlighting in Streamlit

### Export Options
- TXT: Readable dictionary format
- CSV: Summary of extracted entities
- JSON: Full results including all extracted information

### Dataset Mode
- Analyze multiple reports stored in a CSV file
- Example dataset: `medical_reports_100.csv` (100 synthetic entries)
- Can scale to 1000+ entries for research or testing

---

##  Project Structure
┣  medical_report_analyzer.py # Main Streamlit app
┣  medical_reports_100.csv # Sample dataset (100 reports)
┣  requirements.txt # Dependencies
┣  README.md # Project documentation


---

## 🛠 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Krish-Dalsaniya/medical_report_analyzer.git
cd medical_report_analyzer

```
### 2. Install Dependency

pip install -r requirements.txt

### 3. Download spaCy language model

python -m spacy download en_core_web_sm

### 4. Running the Application

streamlit run app.py

