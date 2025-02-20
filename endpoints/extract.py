import json
import os
import re
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import openai

from app.utils.file_extraction import extract_text_from_pdf, extract_text_from_docx
import app.state as state

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

router = APIRouter()

@router.post(
    "/extract-criteria",
    summary="Extract Ranking Criteria from Job Description",
    response_description="A JSON object containing a list of ranking criteria"
)
async def extract_criteria(file: UploadFile = File(...)):
    """
    Upload a job description file (PDF or DOCX) to extract key ranking criteria.
    The criteria are stored for later use.
    """
    if file.content_type == "application/pdf":
        text = extract_text_from_pdf(file)
    elif file.content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        text = extract_text_from_docx(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only PDF and DOCX are supported.")

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
            temperature=0
        )
        criteria_str = response.choices[0].message.content.strip()
        # Remove potential code block formatting.
        criteria_str = re.sub(r'^```(?:json)?', '', criteria_str)
        criteria_str = re.sub(r'```$', '', criteria_str)
        criteria = json.loads(criteria_str)

        if not isinstance(criteria, list):
            raise ValueError("The response from the LLM is not a list.")

        # Store the extracted criteria for later use.
        state.stored_criteria = criteria

        return JSONResponse(content={"criteria": criteria})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
