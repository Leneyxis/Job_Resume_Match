import os
import re
import json
import io
import openai
import pdfplumber
import docx
import pandas as pd
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv

load_dotenv()

# Set your OpenAI API key 
openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

app = FastAPI(
    title="Resume Ranking and Scoring API",
    description=(
        "This API provides two endpoints: one to extract ranking criteria from a job description file "
        "and another to score multiple resumes against those criteria (which are stored after extraction), "
        "returning the results in CSV format."
    ),
    version="1.0.0"
)

# Global variable to store the extracted ranking criteria since we are not making use of a db
stored_criteria = None

### Utility Functions ###

def extract_text_from_pdf(file: UploadFile) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        text = ""
        with pdfplumber.open(file.file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if not text:
            raise ValueError("No text could be extracted from the PDF.")
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_docx(file: UploadFile) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        temp_file_path = "temp_uploaded.docx"
        with open(temp_file_path, "wb") as f:
            f.write(file.file.read())
        doc = docx.Document(temp_file_path)
        text = "\n".join([para.text for para in doc.paragraphs if para.text])
        os.remove(temp_file_path)
        if not text:
            raise ValueError("No text could be extracted from the DOCX.")
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from DOCX: {str(e)}")

### Endpoint 1: Extract Ranking Criteria ###

@app.post(
    "/extract-criteria",
    summary="Extract Ranking Criteria from Job Description",
    response_description="A JSON object containing a list of ranking criteria"
)
async def extract_criteria(file: UploadFile = File(...)):
    """
    Upload a job description file (PDF or DOCX) to extract key ranking criteria.

    - **file**: Job description file in PDF or DOCX format.
    
    Returns a JSON response with a `criteria` key containing a list of extracted ranking criteria.
    The extracted criteria are stored and later used to score resumes.
    """
    # Determine file type and extract text.
    if file.content_type == "application/pdf":
        text = extract_text_from_pdf(file)
    elif file.content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        text = extract_text_from_docx(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only PDF and DOCX are supported.")

    # Prepare a prompt for the LLM to extract ranking criteria.
    prompt = f"""
You are an expert HR recruiter. Analyze the following job description text and extract the key ranking criteria. 
The criteria should include any skills, certifications, experience, and qualifications mentioned. 
Return only a JSON array of strings, where each string is one criterion. Do not include any extra text.

Job Description:
{text}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0  # Deterministic output
        )
        criteria_str = response.choices[0].message.content.strip()
        # Remove potential code block formatting.
        criteria_str = re.sub(r'^```(?:json)?', '', criteria_str)
        criteria_str = re.sub(r'```$', '', criteria_str)
        criteria = json.loads(criteria_str)

        if not isinstance(criteria, list):
            raise ValueError("The response from the LLM is not a list.")

        # Store the extracted criteria for later use.
        global stored_criteria
        stored_criteria = criteria

        return JSONResponse(content={"criteria": criteria})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

### Endpoint 2: Score Resumes Against Stored Criteria ###

@app.post(
    "/score-resumes",
    summary="Score Resumes Against Stored Criteria",
    response_description="A CSV file containing candidate scores"
)
async def score_resumes(
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple resume files (PDF or DOCX) to score resumes against the stored ranking criteria.
    
    The ranking criteria must have been previously extracted using the /extract-criteria endpoint.
    
    For each resume, the endpoint extracts the text and uses an LLM to evaluate the resume against the stored criteria.
    It assigns a score (0-5) for each criterion and computes a total score.
    The final result is returned as a CSV file with columns: `Candidate Name`, each criterion, and `Total Score`.
    """
    global stored_criteria
    if not stored_criteria:
        raise HTTPException(
            status_code=400,
            detail="No stored criteria available. Please extract criteria first using the /extract-criteria endpoint."
        )
    
    criteria_list = stored_criteria
    results = []  # To store scoring results for each resume

    for resume in files:
        # Extract resume text based on file type.
        if resume.content_type == "application/pdf":
            resume_text = extract_text_from_pdf(resume)
        elif resume.content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]:
            resume_text = extract_text_from_docx(resume)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Only PDF and DOCX are supported.")

        # Create a prompt for scoring the resume against the stored criteria.
        prompt = f"""
You are an HR expert evaluating resumes. Evaluate the following resume text against the stored ranking criteria.
For each criterion, assign a score from 0 to 5 (0: no evidence, 5: excellent match).
Extract the candidate's name from the resume text if available; if not, use "Unknown".
Return a JSON object with the following keys:
- "Candidate Name": the candidate's name.
- For each criterion in the stored list, use the exact criterion as a key with its corresponding score (0-5).
- "Total Score": the sum of all individual scores.
Do not include any additional text or explanations.
Resume Text:
{resume_text}
Ranking Criteria:
{json.dumps(criteria_list)}
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful HR assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            response_content = response.choices[0].message.content.strip()
            # Clean up any code block formatting.
            response_content = re.sub(r'^```(?:json)?', '', response_content)
            response_content = re.sub(r'```$', '', response_content)
            score_data = json.loads(response_content)

            # Ensure each stored criterion has a score.
            for crit in criteria_list:
                if crit not in score_data:
                    score_data[crit] = 0

            # Extract candidate name or default to the file name.
            if "Candidate Name" not in score_data or not score_data["Candidate Name"].strip():
                candidate_name = os.path.splitext(resume.filename)[0]
                score_data["Candidate Name"] = candidate_name

            # Recompute the total score from individual criterion scores.
            computed_total = sum(score_data.get(crit, 0) for crit in criteria_list)
            score_data["Total Score"] = computed_total

            results.append(score_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing resume {resume.filename}: {str(e)}")

    # Create a DataFrame with columns: Candidate Name, each criterion, and Total Score.
    columns = ["Candidate Name"] + criteria_list + ["Total Score"]
    df = pd.DataFrame(results, columns=columns)

    # Convert the DataFrame to CSV.
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)

    response_csv = StreamingResponse(stream, media_type="text/csv")
    response_csv.headers["Content-Disposition"] = "attachment; filename=candidate_scores.csv"
    return response_csv

