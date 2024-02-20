from src.services.expenditure_service import run_agent, expenditure_data
from src.services.ocr_service import extract_text_from_image
from pydantic import BaseModel
import boto3
import shutil
import os
import json
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json


router = APIRouter()

class UserMessage(BaseModel):
    user_message: str
    id: str

class UserId(BaseModel):
    id: str



@router.get('/')
async def hello_world():
    return {"message": "Hello, World"}



@router.post("/chat_now")
async def chat_now(data: UserMessage):
    if not data.user_message or not data.id:
        raise HTTPException(status_code=400, detail="user_message and id are required")


    async def stream_agent_responses():
        async for chunk in run_agent(data.user_message, data.id):  # No need to await here
            str_chunk = str(chunk)
            encoded_chunk = str_chunk.encode('utf-8') + b'\n'
            yield encoded_chunk

    return StreamingResponse(stream_agent_responses(), media_type="application/json")




@router.post('/extract_text')
async def extract_text(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail='No selected file')
    
    s3_client = boto3.client('s3', region_name='ap-south-1')
    s3_key_name = f"uploads/{file.filename}"

    try:
        # Save file to disk before uploading to S3
        with open(file.filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        s3_client.upload_file(file.filename, 'persona-agent-storage', s3_key_name)
        file_url = f"https://personal-agent.s3.ap-south-1.amazonaws.com/{s3_key_name}"
        extracted_text = extract_text_from_image(file_url)
        return {"extracted_text": extracted_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/expenditure_data")
async def get_expenditure(data: UserId):
    id = data.id
    print(id)
    try:
        # Ensure the ID is properly formatted or converted as needed before passing to the function
        response = await expenditure_data(id)
        if not data:
            raise HTTPException(status_code=404, detail="Expenditure data not found")
        return {"response": response}
    except ValueError as ve:
        # Handle missing or empty ID
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        # Handle errors from the expenditure_data function
        raise HTTPException(status_code=500, detail=str(re))
