from fastapi import FastAPI
from app.endpoints import extract, score

app = FastAPI(
    title="Resume Ranking and Scoring API",
    description=(
        "This API provides two endpoints: one to extract ranking criteria from a job description file "
        "and another to score multiple resumes against those criteria (which are stored after extraction), "
        "returning the results in CSV format."
    ),
    version="1.0.0"
)

app.include_router(extract.router)
app.include_router(score.router)
