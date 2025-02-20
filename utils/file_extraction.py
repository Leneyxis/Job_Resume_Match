import os
import re
import pdfplumber
import docx
from fastapi import HTTPException, UploadFile

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
