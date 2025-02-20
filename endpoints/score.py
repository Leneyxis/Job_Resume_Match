import json
import os
import re
import io
import openai
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from app.utils.file_extraction import extract_text_from_pdf, extract_text_from_docx
import app.state as state

load_dotenv()

router = APIRouter()

@router.post(
    "/score-resumes",
    summary="Score Resumes Against Stored Criteria",
    response_description="A CSV file containing candidate scores"
)
async def score_resumes(files: list[UploadFile] = File(...)):
    """
    Upload multiple resume files (PDF or DOCX) to score resumes against the stored ranking criteria.
    The result is returned as a CSV file.
    """
    if not state.stored_criteria:
        raise HTTPException(
            status_code=400,
            detail="No stored criteria available. Please extract criteria first using the /extract-criteria endpoint."
        )
    
    criteria_list = state.stored_criteria
    results = []  # To store scoring results for each resume

    for resume in files:
        if resume.content_type == "application/pdf":
            resume_text = extract_text_from_pdf(resume)
        elif resume.content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]:
            resume_text = extract_text_from_docx(resume)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Only PDF and DOCX are supported.")

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
            response_content = re.sub(r'^```(?:json)?', '', response_content)
            response_content = re.sub(r'```$', '', response_content)
            score_data = json.loads(response_content)

            # Ensure every stored criterion has a score.
            for crit in criteria_list:
                if crit not in score_data:
                    score_data[crit] = 0

            if "Candidate Name" not in score_data or not score_data["Candidate Name"].strip():
                candidate_name = os.path.splitext(resume.filename)[0]
                score_data["Candidate Name"] = candidate_name

            # Compute the total score.
            computed_total = sum(score_data.get(crit, 0) for crit in criteria_list)
            score_data["Total Score"] = computed_total

            results.append(score_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing resume {resume.filename}: {str(e)}")

    # Create a DataFrame and convert it to CSV.
    columns = ["Candidate Name"] + criteria_list + ["Total Score"]
    df = pd.DataFrame(results, columns=columns)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)

    response_csv = StreamingResponse(stream, media_type="text/csv")
    response_csv.headers["Content-Disposition"] = "attachment; filename=candidate_scores.csv"
    return response_csv
