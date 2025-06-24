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
    try:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image)
    except Exception as e:
        return f"Image processing failed: {str(e)}"

# Helper function to extract fields
def extract_field(pattern, text, group=1):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else None

# Resume field parser
def extract_resume_data(text):
    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    full_text = "\n".join(lines)

    name = None
    for line in lines[:5]:
        if re.match(r'^[A-Za-z\'-]+\s+[A-Za-z\'-]+$', line):
            name = line.strip().title()  # Normalize to Title Case
            break


    # Extract other basic fields
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', full_text)
    email = email_match.group(0) if email_match else None

    phone_match = re.search(r'(\+?\d[\d\s()-]{7,}\d)', full_text)
    phone = phone_match.group(1) if phone_match else None

    gender = extract_field(r'Gender\s*[:\-]?\s*(Male|Female|Other)', full_text)
    dob = extract_field(r'Date of Birth\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', full_text)

    # Age calculation
    age = None
    if dob:
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]:
            try:
                dob_date = datetime.strptime(dob, fmt)
                age = datetime.today().year - dob_date.year
                break
            except ValueError:
                continue

    # === Extract Education Section ===
    # edu_section = re.search(r'(Education|Educational Background)(.*?)(?=\n[A-Z][a-z]+|$)', full_text, re.DOTALL | re.IGNORECASE)
    edu_section = re.search(
    r'(Education|Educational Background)[\s:\-]*\n(.*?)(?=\n[A-Z\s]{3,}:?|\Z)', 
    full_text, 
    re.DOTALL | re.IGNORECASE
    )
    university = degree = major = gpax = grad_year = None
    if edu_section:
        edu_text = edu_section.group(2)

        university_match = re.search(r'(university|institute|college)[^\n]*', edu_text, re.IGNORECASE)
        if university_match:
            university = university_match.group(0).strip()

        degree_match = re.search(r'(?i)(bachelor|master|doctor)[^\n]*', edu_text)
        if degree_match:
            degree = degree_match.group(0).strip()

        major_match = re.search(r'(?i)(major\s*[:\-]?\s*)([^\n,]+)', edu_text)
        if major_match:
            major = major_match.group(2).strip()

        gpax_match = re.search(r'(GPAX|GPA)\s*[:\-]?\s*([\d.]+)', edu_text)
        if gpax_match:
            gpax = gpax_match.group(2).strip()

        grad_match = re.search(r'Graduation\s*(Year)?\s*[:\-]?\s*(\d{4})', edu_text)
        if grad_match:
            grad_year = grad_match.group(2).strip()

    # === Extract Skills Section ===
    skills_section = re.search(r'(Skills|Technologies|Tools|Soft Skills)(.*?)(?=\n[A-Z][a-z]+|$)', full_text, re.IGNORECASE | re.DOTALL)
    skills = []
    if skills_section:
        skill_text = skills_section.group(2)
        # Clean skills, make them unique and properly capitalized
        skills = list({s.strip().title() for s in re.split(r'[,•;|]', skill_text) if re.search(r'[a-zA-Z]', s)})
    skills = skills if skills else None

    # === Extract Work Experience Section (Multiple Entries) ===
    experience_list = []
    experience_blocks = re.findall(
        r'(?i)(Company\s*[:\-]?\s*(.*?)\n)?'
        r'(Position\s*[:\-]?\s*(.*?)\n)?'
        r'((?:\w{3,9}\s\d{4})\s*[-–]\s*(?:\w{3,9}\s\d{4}|Present))\n'
        r'((?:[-•*].*\n?)+)',
        full_text
    )
    for block in experience_blocks:
        exp = {
            "Company": block[1].strip() if block[1] else None,
            "Position": block[3].strip() if block[3] else None,
            "Duration": block[4].strip(),
            "Responsibilities": [line.strip("•*- ") for line in block[5].splitlines() if line.strip()]
        }
        experience_list.append(exp)

    return {
        "Name": name,
        "Gender": gender,
        "Date of Birth": dob,
        "Age": age,
        "Email": email,
        "Tel": phone,
        "University": university,
        "Degree": degree,
        "Major": major,
        "Gpax": gpax,
        "Graduation Year": grad_year,
        "Skills": skills,
        "Experience": experience_list if experience_list else None
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

    parsed_data = extract_resume_data(text)

    return {
        "raw_text": text,
        "parsed_data": parsed_data
    }
