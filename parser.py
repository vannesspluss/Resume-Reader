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
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text = "\n".join(lines)

    # Name
    name = None
    for line in lines[:5]:
        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', line):
            name = line
            break
    if not name:
        email_match = re.search(r'([a-z]+)\.([a-z]+)@', full_text, re.IGNORECASE)
        if email_match:
            name = f"{email_match.group(1).capitalize()} {email_match.group(2).capitalize()}"

    # Email and phone
    email = extract_field(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', full_text)
    phone = extract_field(r'(\+?\d[\d\s().-]{7,}\d)', full_text)

    gender = extract_field(r'Gender\s*[:\-]?\s*(Male|Female|Other)', full_text)
    dob = extract_field(r'Date of Birth\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', full_text)

    age = None
    if dob:
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]:
            try:
                dob_date = datetime.strptime(dob, fmt)
                age = datetime.today().year - dob_date.year
                break
            except ValueError:
                continue

    # Education block (more flexible)
    edu_section = re.search(r'(Education|EDUCATION|Educational Background)(.*?)(?=\n[A-Z][a-z]+|\nPROFILE|\nSKILLS|\nEXPERIENCE|$)', full_text, re.DOTALL)
    university = degree = major = gpax = grad_year = None
    if edu_section:
        edu_text = edu_section.group(2)

        university = extract_field(r'(University|Institute|College)[^\n]*', edu_text)
        degree = extract_field(r'(Bachelor|Master|Ph\.?D)[^\n]*', edu_text)
        major = extract_field(r'(Major\s*[:\-]?\s*)([^\n,]+)', edu_text, group=2)
        gpax = extract_field(r'(GPAX|GPA)\s*[:\-]?\s*([\d.]+)', edu_text, group=2)
        grad_year = extract_field(r'\b(20\d{2})\b', edu_text)

    # Skills (case insensitive)
    skills = []
    skills_section = re.search(r'(Skills|SKILLS|Technologies|Tools|Soft Skills)(.*?)(?=\n[A-Z][a-z]+|\nPROJECTS|\nEXPERIENCE|$)', full_text, re.IGNORECASE | re.DOTALL)
    if skills_section:
        for line in skills_section.group(2).splitlines():
            if re.search(r'[a-zA-Z]', line):
                skills.extend([s.strip() for s in re.split(r'[,•;|]', line) if s.strip()])
    skills = list(set(skills)) if skills else None

    # Work Experience (fallback even without Position/Company)
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

    return extract_resume_data(text)
