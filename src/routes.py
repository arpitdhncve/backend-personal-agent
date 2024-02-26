from venv import create
from src.services.expenditure_service import run_agent, expenditure_data
from src.services.ocr_service import extract_text_from_image
from pydantic import BaseModel
import boto3
import shutil
import os
import json
from fastapi import APIRouter, HTTPException, File, UploadFile, status, Depends, Header, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import httpx
import jwt
import base64
import requests
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid

customerId = "C-E98F177B0E2E40E"   #id for message central

router = APIRouter()

class UserMessage(BaseModel):
    user_message: str
    id: str


class UserId(BaseModel):
    id: str


class SignUpRequest(BaseModel):
    phone_number: str
    country_code: str = '91'  # Default to '91' if not specified


class VerifyOTPRequest(BaseModel):
    phone_number: str
    verification_id: str
    otp_code: str


SECRET_KEY = "QWERTYUIORFCGHHGFD123456trfdsscvfgh"  # Generates a URL-safe text string, containing 64 bytes of random data
ALGORITHM = "HS256"




def create_jwt_token(data: dict):
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt





def generate_token_message_central():
    # Encode the password in Base-64
    password = "Greenwood@123"
    encoded_password = base64.b64encode(password.encode()).decode()

    # Base URL
    url = 'https://cpaas.messagecentral.com/auth/v1/authentication/token?country=IN&customerId=C-E98F177B0E2E40E&key=R3JlZW53b29kQDEyMw==&scope=NEW'


    # Set the accept header
    headers = {'accept': '*/*'}

    # Send the GET request with the parameters
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response to get the token
        token = response.json().get('token')
        return token
    else:
        # Handle errors or unsuccessful requests
        return f"Error: {response.status_code}, {response.text}"




async def get_current_user(auth_token: str = Header(None, alias='authToken')):
    if auth_token is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        # Assuming the token prefix is "Bearer", strip it off
        token = auth_token.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone_number = payload.get("phone_number")  # Extract the phone number instead of id
        if phone_number is None:
            raise HTTPException(status_code=401, detail="Invalid JWT token")
        return phone_number
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")






@router.get('/')
async def hello_world():
    return {"message": "Hello, World"}







@router.post("/sign_up")
async def sign_up(sign_up_request: SignUpRequest):
    url = f'https://cpaas.messagecentral.com/verification/v2/verification/send?countryCode={sign_up_request.country_code}&customerId=C-E98F177B0E2E40E&flowType=SMS&otpLength=4&mobileNumber={sign_up_request.phone_number}'

    
    # Create a message central token
    token = generate_token_message_central()
    
    # Set the authToken in headers as required
    headers = {
        'authToken': token,
        'Content-Type': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
    

    if response.status_code == 200:
        response_data = response.json()  # This line parses the JSON response body into a dictionary
        # Now you can subscript response_data to access its contents
        return {"data": response_data["data"], "message_central_token": token, "message" : "OTP Sent successfully"}

    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send SMS.")
    




@router.post("/verify_otp")
async def verify_otp(request_body: VerifyOTPRequest, auth_token: str = Header(None, alias='authToken')):
    if auth_token is None:
        raise HTTPException(status_code=400, detail="authToken header missing")

    url = f"https://cpaas.messagecentral.com/verification/v2/verification/validateOtp?countryCode=91&mobileNumber={request_body.phone_number}&verificationId={request_body.verification_id}&customerId=C-E98F177B0E2E40E&code={request_body.otp_code}"
     # Assuming the token prefix is "Bearer", strip it off
    auth_token = auth_token.split(" ")[1]
    headers = {'authToken': auth_token}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        jwt_token = create_jwt_token({
            'phone_number': request_body.phone_number,
        })
        return {"data": response_data.get("data"), "jwt_token": jwt_token, "message": "OTP Verified successfully"}
    else:
        # It's a good practice to log the error details for debugging purposes
        # Log response.text or response.json() as needed
        raise HTTPException(status_code=500, data="Failed to verify OTP.")



@router.post("/chat_now")
async def chat_now(request:Request, data: UserMessage, phone_number: str = Depends(get_current_user)):
    print(request.headers)
    if not data.user_message or not data.id:
        raise HTTPException(status_code=400, detail="user_message and id are required")


    async def stream_agent_responses():
        async for chunk in run_agent(data.user_message, data.id):  # No need to await here
            # Convert the chunk to a string if it is not one, and remove newline characters
            str_chunk = str(chunk).replace('\n', ' ').replace('\r', '')
            # Escape double quotes correctly for JSON, but avoid adding unnecessary backslashes
            str_chunk = str_chunk.replace('"', '\\"')
            # Wrap the modified string in a dictionary
            chunk_dict = {"message": str_chunk}
            # Convert the dictionary to a JSON string
            json_chunk = json.dumps(chunk_dict)
            # Encode the JSON string
            encoded_chunk = json_chunk.encode('utf-8') + b'\n'  # Keeping the newline here for separate JSON objects in the stream
            yield encoded_chunk
        

    return StreamingResponse(stream_agent_responses(), media_type="application/json")




@router.post('/extract_text')
async def extract_text(file: UploadFile = File(...), phone_number: str = Depends(get_current_user)):
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
        return {"data": extracted_text, "message":"text extracted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/expenditure_data")
async def get_expenditure(data: UserId, phone_number: str = Depends(get_current_user)):
    id = data.id
    try:
        # Ensure the ID is properly formatted or converted as needed before passing to the function
        response = await expenditure_data(id)
        if not response:
            raise HTTPException(status_code=404, detail="Expenditure data not found")
        return {"data": response, "message":"Data Available"}
    except ValueError as ve:
        # Handle missing or empty ID
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        # Handle errors from the expenditure_data function
        raise HTTPException(status_code=500, detail=str(re))





