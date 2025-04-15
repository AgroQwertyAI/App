import os
import logging
from typing import List

import torch
from torch.nn import functional as F
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import BertTokenizerFast, BertForSequenceClassification
from dotenv import load_dotenv

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Loading environment variables
load_dotenv()
API_PORT = int(os.getenv("API_PORT", 52004))

# FastAPI initialization
app = FastAPI(
    title="Classification Service",
    description="Service for classifying messages using BERT model",
    version="0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model configuration
MODEL_NAME = "AgroQwertyAI/berta_report_classifier"
ID2LABEL = {0: "другое", 1: "отчёт"}
LABEL2ID = {"другое": 0, "отчёт": 1}

# Check CUDA availability
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

# Initializing tokenizer and model
tokenizer = BertTokenizerFast.from_pretrained(MODEL_NAME)
model = BertForSequenceClassification.from_pretrained(MODEL_NAME)
model.to(device)
model.eval()  # Set evaluation mode

# Data models
class ClassificationRequest(BaseModel):
    text: str = Field(..., description="Text for classification")


class ClassificationResponse(BaseModel):
    report: float = Field(..., description="Вероятность класса 'отчёт'")
    non_report: float = Field(..., alias="non-report", description="Вероятность класса 'другое'")

    class Config:
        populate_by_name = True


class BatchClassificationResponse(BaseModel):
    results: List[ClassificationResponse]


async def classify_text(text: str) -> ClassificationResponse:
    """Classifies text and returns probabilities for both classes."""
    try:
        # Токенизация входного текста
        inputs = tokenizer(
            text,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits

        # Преобразование логитов в вероятности
        probabilities = F.softmax(logits, dim=1)
        non_report_prob = round(float(probabilities[0][0].item()), 3)  # Class 'other' with 3 digits
        report_prob = round(float(probabilities[0][1].item()), 3)  # Class 'report' with 3 digits

        return ClassificationResponse(report=report_prob, non_report=non_report_prob)
    except Exception as e:
        logger.error(f"Error classifying text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")


@app.post("/classify", response_model=ClassificationResponse)
async def classify_endpoint(request: ClassificationRequest):
    """Endpoint for classifying a single text."""
    return await classify_text(request.text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=API_PORT)
