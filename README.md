# Job_Resume_Match
An app that automates the process of ranking resumes based on job descriptions.

---
# Resume Ranking and Scoring API

This FastAPI application provides two endpoints to automate the process of extracting ranking criteria from job descriptions and scoring resumes based on those criteria. The application leverages OpenAI's language model (using the `gpt-4o` model in this example) to process text data from PDF and DOCX files, and it returns structured JSON or CSV outputs.

## Features

- **Extract Ranking Criteria:**  
  Upload a job description file (PDF or DOCX) to extract key ranking criteria (skills, certifications, experience, qualifications) using an LLM.
  
- **Score Resumes:**  
  Upload multiple resumes (PDF or DOCX) to score them against the previously stored ranking criteria. The API returns a CSV file containing individual scores per criterion and a total score per candidate.

- **Interactive Documentation:**  
  Swagger UI is provided for easy testing and documentation at `/docs`.

## Prerequisites

- Python 3.7 or higher
- An OpenAI API key (you can obtain one from [OpenAI](https://openai.com/api/))
- Required libraries:
  - FastAPI
  - Uvicorn
  - OpenAI
  - pdfplumber
  - python-docx
  - Pandas
  - python-dotenv

## Installation

1. **Clone the Repository:**
2. **Create a Virtual Environment (Optional but Recommended):**
3. **Install Dependencies:**
   
## Configuration

1. **Create a `.env` File:**
   In the root directory of your project, create a `.env` file.

2. **Add Your OpenAI API Key:**
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Running the Application

Start the application using Uvicorn:

```bash
uvicorn main:app --reload
```

The API will be available at:  
[http://127.0.0.1:8000](http://127.0.0.1:8000)

## API Endpoints

### 1. Extract Ranking Criteria

- **Endpoint:** `/extract-criteria`
- **Method:** `POST`
- **Description:**  
  Upload a job description file (PDF or DOCX) to extract key ranking criteria. The extracted criteria are stored in the application for later use in scoring resumes.
- **Request:**  
  - **file:** A PDF or DOCX file containing the job description.
- **Response:**  
  Returns a JSON object with a key `criteria` that contains an array of ranking criteria.
- **Example Response:**
  ```json
  {
    "criteria": [
      "5+ years of experience in Python development",
      "Expertise in machine learning",
      "Bachelor's degree in Computer Science"
    ]
  }
  ```

### 2. Score Resumes Against Stored Criteria

- **Endpoint:** `/score-resumes`
- **Method:** `POST`
- **Description:**  
  Upload multiple resume files (PDF or DOCX) to score them against the stored ranking criteria extracted previously.  
  **Note:** Ensure you have first called `/extract-criteria` to store the ranking criteria.
- **Request:**  
  - **files:** One or more resume files in PDF or DOCX format.
- **Response:**  
  Returns a CSV file containing the candidate's name, scores for each criterion, and the total score.
- **Example CSV Output:**
  ```
  Candidate Name,5+ years of experience in Python development,Expertise in machine learning,Bachelor's degree in Computer Science,Total Score
  John Doe,5,4,3,12
  Jane Smith,4,5,4,13
  ```

## Swagger UI

After running the application, you can access the interactive Swagger UI documentation at:
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## License

This project is licensed under the [MIT License](LICENSE).
