import pdfplumber
import pytesseract
from PIL import Image
import docx2txt
import re
import os

# Text extractors
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(docx_path):
    return docx2txt.process(docx_path)

def extract_text_from_image(image_path):
    image = Image.open(image_path)
    return pytesseract.image_to_string(image)

# Resume field parser
def extract_resume_data(text):
    email = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    phone = re.search(r'(\+?\d[\d\s()-]{7,}\d)', text)
    name = re.search(r'(?i)(Name\s*[:\-]?\s*)([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text)

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
        "Name": name.group(2) if name else None,
        "Email": email.group() if email else None,
        "Phone": phone.group() if phone else None,
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
