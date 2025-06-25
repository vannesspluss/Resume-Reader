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
        if re.match(r'^[A-Za-z\'\-]+\s+[A-Za-z\'\-\s]+$', line) and len(line.split()) <= 4:
            name = re.sub(r'\s+', ' ', line).strip().title()
            break

    # --- Basic fields ---
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', full_text)
    email = email_match.group(0) if email_match else None

    phone_match = re.search(r'(\+?\d[\d\s()-]{7,}\d)', full_text)
    phone = phone_match.group(1) if phone_match else None

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
    # university = degree = major = gpax = grad_year = None

    # edu_section = re.search(r'(EDUCATION|Education|Educational Background)[\s:\-]*\n(.*?)(?=\n[A-Z\s]{3,}:?|\Z)', full_text, re.DOTALL | re.IGNORECASE)
    # if edu_section:
    #     edu_text = edu_section.group(2)

    #     university_match = re.search(r'((?:University|College|Institute)\s+of\s+[^\n,]+|[^\n,]+(?:University|Uollege|Institute)[^\n,]*|[A-Z][^\n,]*(University|College|Institute)[^\n,]*)', edu_text, re.IGNORECASE)
    #     if university_match:
    #         university = university_match.group(0).strip()

    #     degree_match = re.search(r'(?i)(BACHELOR|MASTER|DOCTOR|Bachelor|Master|Doctor|bachelor|master|doctor)[^\n,]*', edu_text)
    #     if degree_match:
    #         degree = degree_match.group(0).strip()

    #     major_match = re.search(r'(?i)(MAJOR|major)\s*[:\-]?\s*([^\n,]+)', edu_text)
    #     if major_match:
    #         major = major_match.group(1).strip()
    #     else:
    #         degree_major_match = re.search(r'(?:BACHELOR|MASTER|DOCTOR|Bachelor|Master|Doctor|bachelor|master|doctor)\s+of\s+([^\n,]+)', edu_text, re.IGNORECASE)
    #         if degree_major_match:
    #             major = degree_major_match.group(1).strip()
    #         else:
    #             degree_major_match = re.search(r'(?i)(Bachelor|Master|Doctor)[’''s]*\s+(Degree)?\s*(of|in)?\s+([^\n,]+)',edu_text)
    #             if degree_major_match:
    #                 major = degree_major_match.group(1).strip() 


    #     gpax_match = re.search(r'(GPAX|GPA)\s*[:\-]?\s*([\d.]+)', edu_text)
    #     if gpax_match:
    #         gpax = float(gpax_match.group(2).strip())
    #     else:
    #         gpax_match = re.search(r'(?i)(GPA|GPAX)\s*[:\-]?\s*([\d.]+)', edu_text)
    #         if gpax_match:
    #             gpax = float(gpax_match.group(2).strip())

    #     grad_match = re.search(r'(Graduation\s*(Year)?|Study Period)\s*[:\-]?\s*(\d{4})\s*(?:[-–]\s*(\d{4}|Present))?', edu_text, re.IGNORECASE)
    #     if grad_match:
    #         grad_year = grad_match.group(3)
    #     else:
    #         range_match = re.search(r'(?i)(\d{4})\s*[-–]\s*(\d{4}|Present)', edu_text)
    #         if range_match:
    #             grad_year = range_match.group(2)
    
    edu_section = re.search(r'(?i)(EDUCATION|Educational Background)[\s:\-]*\n(.*?)(?=\n[A-Z][A-Z\s]{2,}[:\-]|\Z)', full_text, re.DOTALL)
    university = degree = major = gpax = grad_year = None

    if edu_section:
        edu_text = edu_section.group(2)
        edu_lines = [line.strip() for line in edu_text.split("\n") if line.strip()]

        for i, line in enumerate(edu_lines):
            if re.search(r'(University|College|Institute)', line, re.IGNORECASE):
                university = line.strip()
                for j in range(i+1, min(i+4, len(edu_lines))):
                    deg_match = re.search(r'(Bachelor|Master|Doctor)[^,\n]*', edu_lines[j], re.IGNORECASE)
                    if deg_match:
                        degree = deg_match.group(0).strip()

                    major_match = re.search(r'(?i)(Program|Major)\s*(in|of)?\s*([^\n,]+)', edu_lines[j])
                    if major_match:
                        major = major_match.group(3).strip()

                    gpax_match = re.search(r'(GPA|GPAX)\s*[:\-]?\s*([\d.]+)', edu_lines[j], re.IGNORECASE)
                    if gpax_match:
                        gpax = float(gpax_match.group(2).strip())
                break


    # --- Skills extraction ---
    skills_section = re.search(r'(?i)(SKILLS|Skill Set|Technologies|Frameworks and Libraries|Tools|Soft Skills)\s*\n(.*?)(?=\n[A-Z][A-Z ]{2,}|$)', full_text, re.DOTALL)
    skills = []
    structured_skills = {}

    if skills_section:
        skill_text = skills_section.group(2).strip()

        # Split by newlines where a subsection starts, like "Programming:"
        subsections = re.split(r'\n(?=[A-Za-z ]+:\s*)', skill_text)

        for section in subsections:
            if ":" in section:
                header, items = section.split(":", 1)
                header = header.strip().title()
                item_list = [s.strip().title() for s in re.split(r'[,•;|]\s*', items) if re.search(r'[a-zA-Z]', s)]
                structured_skills[header] = item_list
            else:
                # For lines without a subsection header, handle loosely
                loose_items = [s.strip().title() for s in re.split(r'[,•;|]\s*', section) if re.search(r'[a-zA-Z]', s)]
                if loose_items:
                    structured_skills.setdefault("General", []).extend(loose_items)

        # Optional flat list of all skills
        skills = [skill for sublist in structured_skills.values() for skill in sublist]




    # --- Experience extraction ---
    experience_list = []
    experience_blocks = re.findall(
        r'(?i)(Company\s*[:\-]?\s*(.*?)\n)?(Position\s*[:\-]?\s*(.*?)\n)?((?:\w{3,9}\s\d{4})\s*[-–]\s*(?:\w{3,9}\s\d{4}|Present))\n((?:[-•*].*\n?)+)',
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
