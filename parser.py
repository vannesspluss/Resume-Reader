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

# Resume field parser (unchanged from your version)
def extract_resume_data(text):
    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    full_text = "\n".join(lines)

    # --- Name extraction ---
    name = None
    for line in lines[:10]:
        if re.match(r'^[A-Za-z\'\-]+\s+[A-Za-z\'\-]+$', line) and len(line.split()) <= 4:
            name = line.title()
            break

    # --- Basic fields ---
    email = extract_field(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', full_text)
    phone = extract_field(r'(\+?\d[\d\s()-]{7,}\d)', full_text)
    gender = extract_field(r'Gender\s*[:\-]?\s*(Male|Female|Other)', full_text)
    dob = extract_field(r'Date of Birth\s*[:\-]?\s*([\d]{1,2}[-/][\d]{1,2}[-/][\d]{2,4})', full_text)

    age = None
    if dob:
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]:
            try:
                dob_date = datetime.strptime(dob, fmt)
                age = datetime.today().year - dob_date.year
                break
            except ValueError:
                continue

    # --- Education extraction ---
    university = degree = major = gpax = grad_year = None
    edu_match = re.search(r'(education|educational background)\s*(.*?)(experience|projects|skills|$)', full_text, re.IGNORECASE | re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(2)

        university_match = re.search(r'([A-Z][^\n,]*(University|College|Institute)[^\n,\n]*)', edu_text, re.IGNORECASE)
        if university_match:
            university = university_match.group(0).strip()

        degree_match = re.search(r'\b(Bachelor|Master|Doctor)[^\n,]*', edu_text, re.IGNORECASE)
        if degree_match:
            degree = degree_match.group(0).strip()

        major_match = re.search(r'\b(in|major\s*[:\-]?)\s*([^\n,]+)', edu_text, re.IGNORECASE)
        if major_match:
            major = major_match.group(2).strip()

        gpax_match = re.search(r'(GPA|GPAX)\s*[:\-]?\s*([\d.]+)', edu_text, re.IGNORECASE)
        if gpax_match:
            gpax = float(gpax_match.group(2).strip())

        grad_match = re.search(r'(Graduation\s*(Year)?|Study Period)\s*[:\-]?\s*(\d{4})', edu_text, re.IGNORECASE)
        if grad_match:
            grad_year = grad_match.group(3)

    # --- Skills extraction ---
    skills_section = re.search(r'(SKILL|SKILLS|skills\s*&?\s*strengths|skills|technologies|tools|soft skills)(.*?)(projects|experience|$)', full_text, re.IGNORECASE | re.DOTALL)
    skills = []
    if skills_section:
        skill_text = skills_section.group(2)
        skill_lines = re.split(r'[\n,•;]', skill_text)
        skills = [s.strip() for s in skill_lines if s.strip() and re.search(r'[a-zA-Z]', s)]
    skills = skills if skills else None

    # --- Experience extraction ---
    experience_list = []
    exp_pattern = re.compile(r'(.+?)\s+for\s+(.+?)\s+(\w+\s+\d{4}\s*-\s*(?:\w+\s+\d{4}|Present))', re.IGNORECASE)
    i = 0
    while i < len(lines):
        exp_match = exp_pattern.match(lines[i])
        if exp_match:
            position = exp_match.group(1).strip()
            company = exp_match.group(2).strip()
            duration = exp_match.group(3).strip()
            responsibilities = []
            i += 1
            while i < len(lines) and re.match(r'^[-•]', lines[i]):
                responsibilities.append(lines[i].lstrip('-• ').strip())
                i += 1
            experience_list.append({
                "Company": company,
                "Position": position,
                "Duration": duration,
                "Responsibilities": responsibilities
            })
        else:
            i += 1

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
