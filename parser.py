import pdfplumber
import pytesseract
from PIL import Image
import docx2txt
import re
import os
from datetime import datetime

# File text extractors
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

# Field extraction helper
def extract_field(pattern, text, group=1, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    return match.group(group).strip() if match else None

# Resume parser
def extract_resume_data(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text = "\n".join(lines)

    # Name detection
    name = None
    for line in lines[:5]:
        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', line):
            name = line
            break
    if not name:
        email_name = re.search(r'^([a-z]+)\.([a-z]+)@', full_text, re.IGNORECASE)
        if email_name:
            name = f"{email_name.group(1).capitalize()} {email_name.group(2).capitalize()}"

    # Basic details
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

    # Education extraction
    university = degree = major = gpax = grad_year = None
    edu_block = re.search(r'(EDUCATION|Education)(.*?)(?=\n[A-Z][a-z]+|\nPROFILE|\nSKILLS|\nEXPERIENCE|$)', full_text, re.DOTALL)
    if edu_block:
        edu_text = edu_block.group(2)
        university = extract_field(r'(University|Institute|College)[^\n]*', edu_text)
        degree = extract_field(r'(Bachelor|Master|Ph\.?D)[^\n]*', edu_text)
        major = extract_field(r'(Major\s*[:\-]?\s*)([^\n,]+)', edu_text, group=2)
        gpax = extract_field(r'(GPAX|GPA)\s*[:\-]?\s*([\d.]+)', edu_text, group=2)
        grad_year = extract_field(r'(\b20\d{2}\b)', edu_text)

    # Skills
    skills = []
    skill_block = re.search(r'(Skills|SKILLS|Technologies|Soft Skills)(.*?)(?=\n[A-Z][a-z]+|\nPROJECTS|\nEXPERIENCE|$)', full_text, re.DOTALL)
    if skill_block:
        for line in skill_block.group(2).splitlines():
            if any(c.isalpha() for c in line):
                skills += [s.strip() for s in re.split(r'[•,;|]', line) if s.strip()]
    skills = sorted(set(skills)) if skills else None

    # Experience
    experience_list = []
    exp_matches = re.findall(
        r'(?:Company\s*[:\-]?\s*(.*?)\n)?'
        r'(?:Position\s*[:\-]?\s*(.*?)\n)?'
        r'((?:\w+\s*\d{4})\s*[-–]\s*(?:\w+\s*\d{4}|Present))\n'
        r'((?:[-•*].*\n?)+)',
        full_text, re.IGNORECASE
    )
    for match in exp_matches:
        experience_list.append({
            "Company": match[0].strip() if match[0] else None,
            "Position": match[1].strip() if match[1] else None,
            "Duration": match[2].strip(),
            "Responsibilities": [x.strip("•*- ") for x in match[3].splitlines() if x.strip()]
        })

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
        "Experience": experience_list or None
    }

# Auto file type detector
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
