import pdfplumber
import pytesseract
from PIL import Image
import docx2txt
import re
import os
from datetime import datetime

# Text extractors
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_text_from_docx(docx_path):
    return docx2txt.process(docx_path)

def extract_text_from_image(image_path):
    image = Image.open(image_path)
    return pytesseract.image_to_string(image)

# Helper function to extract fields
def extract_field(pattern, text, group=1):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else None

# Resume field parser
def extract_resume_data(text):
    # Basic fields
    name = extract_field(r'Name\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text)
    gender = extract_field(r'Gender\s*[:\-]?\s*(Male|Female|Other)', text)
    dob = extract_field(r'Date of Birth\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
    university = extract_field(r'University\s*[:\-]?\s*(.+)', text)
    degree = extract_field(r'Bachelor/Master/Doctor\s*[:\-]?\s*(.+)', text)
    major = extract_field(r'Major\s*[:\-]?\s*(.+)', text)
    gpax = extract_field(r'(?:GPAX|GPA)\s*[:\-]?\s*([\d.]+)', text)
    grad_year = extract_field(r'Graduation\s*(?:Year)?\s*[:\-]?\s*(\d{4})', text)
    skills = re.findall(r'\b(?:Skills?|Technologies?|Soft Skills?|Strengths?)\b\s*[:\-]?\s*(.*)', text, re.IGNORECASE)

    # Age calculation
    age = None
    if dob:
        try:
            dob_date = datetime.strptime(dob, "%d/%m/%Y")
            age = datetime.today().year - dob_date.year
        except ValueError:
            pass

    # Experience parsing
    experience_pattern = re.compile(
        r'(?i)(Company\s*[:\-]?\s*)(?P<company>.*?)\s*[\n\r]+'
        r'(Position\s*[:\-]?\s*)(?P<position>.*?)\s*[\n\r]+'
        r'(?P<duration>(?:\w{3,9}\s\d{4})\s*[-–]\s*(?:\w{3,9}\s\d{4}))\s*[\n\r]+'
        r'(?P<responsibilities>(?:[-•*].*\n?)+)', re.IGNORECASE)

    match = experience_pattern.search(text)
    experience = {}
    if match:
        experience = {
            "Company": match.group("company").strip(),
            "Position": match.group("position").strip(),
            "Duration": match.group("duration").strip(),
            "Responsibilities": [line.strip("•*- ") for line in match.group("responsibilities").splitlines() if line.strip()]
        }

    return {
        "Name": name,
        "Gender": gender,
        "Date of Birth": dob,
        "Age": age,
        "University": university,
        "Degree": degree,
        "Major": major,
        "Gpax": gpax,
        "Graduation Year": grad_year,
        "Skills": skills[0].split(',') if skills else None,
        "Experience": experience
    }

# Wrapper to detect file type and extract
def parse_resume(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        text = extract_text_from_image(file_path)
    else:
        return {"error": "Unsupported file format"}

    return extract_resume_data(text)
