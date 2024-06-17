from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Body
from sqlalchemy.orm import Session
from . import models, schemas, crud, database, utils
from transformers import pipeline
import os

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create directories
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Question-Answering pipeline
qa_pipeline = pipeline("question-answering", model="deepset/roberta-base-squad2")

@app.post("/upload/", response_model=schemas.PDFDocument)
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    text_content = utils.extract_text_from_pdf(file_location)
    pdf_create = schemas.PDFDocumentCreate(filename=file.filename, text_content=text_content)
    pdf = crud.create_pdf_document(db=db, pdf=pdf_create)
    return pdf

@app.get("/pdf/{pdf_id}", response_model=schemas.PDFDocument)
def read_pdf(pdf_id: int, db: Session = Depends(get_db)):
    db_pdf = crud.get_pdf_document(db, pdf_id=pdf_id)
    if db_pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    return db_pdf

@app.post("/question/")
def ask_question(question_request: schemas.QuestionRequest, db: Session = Depends(get_db)):
    db_pdf = crud.get_pdf_document(db, pdf_id=question_request.pdf_id)
    if db_pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    answer = qa_pipeline(question=question_request.question, context=db_pdf.text_content)
    return {"question": question_request.question, "answer": answer["answer"]}
