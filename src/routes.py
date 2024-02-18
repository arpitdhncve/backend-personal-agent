from src import app
from flask import Flask, request, Response, jsonify, Blueprint, current_app
from src.services.expenditure_service import run_agent
from src.services.ocr_service import extract_text_from_image  # Ensure you create this service
from werkzeug.utils import secure_filename
import os
import boto3


routes = Blueprint('api', __name__)

@routes.route('/', methods = ['GET'])
def hello_world():
    return jsonify(message="Hello, World")


@routes.route('/chat_now', methods=['POST'])
def update_expenditure():
    data = request.json
    user_message = data.get('user_message')
    id = data.get('id')

    if user_message is None or id is None:
        return jsonify({'error': 'user_message and id are required'}), 400

    # Call extract_expenditure function
    result = run_agent(user_message, id)
    print(result)
    return jsonify({'result': result["output"]}), 200



@routes.route('/extract_text', methods=['POST'])
def extract_text():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Configure boto3 client
        s3_client = boto3.client('s3', region_name='ap-south-1')
        
        # Generate an S3 key name for the uploaded file
        s3_key_name = f"uploads/{filename}"
        
        # Upload the file to S3
        try:
            s3_client.upload_fileobj(file, 'persona-agent-storage', s3_key_name)
            # Assuming extract_text_from_image can now take the S3 object URL or you adjust its logic
            file_url = f"https://personal-agent.s3.ap-south-1.amazonaws.com/{s3_key_name}"
            print(f's3 file url : {file_url}')
            # Adjust extract_text_from_image to work with file_url or directly download the file to process
            extracted_text = extract_text_from_image(file_url)  # Placeholder for OCR result
            print(f'extracted_Text from image: {extracted_text}')
            return jsonify({'extracted_text': extracted_text}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500







