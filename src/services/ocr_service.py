import easyocr
import os
import boto3
from werkzeug.utils import secure_filename
import re
from langsmith import Client
from langchain import hub
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, FewShotChatMessagePromptTemplate
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts.prompt import PromptTemplate
from uuid import uuid4

#write env variables here

client = Client()
unique_id = uuid4().hex[0:8]




llm = ChatOpenAI(temperature = 0.0)


#what user wants chain

caption_text_from_image_system_prompt = """  You have given some important piece of information in array of\
jumbeled words. This information is important for user to save. \
You have to recreate information using the input and save it.
"""

prompt_to_get_what_user_wants = ChatPromptTemplate.from_messages(
    [
        ("system", caption_text_from_image_system_prompt),
        # MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ]
)

what_user_wants_chain = prompt_to_get_what_user_wants | llm | StrOutputParser()

# Replace with your bucket name and object key
bucket_name = "persona-agent-storage"

def extract_string_after_amazonaws(url, regex):
  """
  Extracts the string after "amazonaws.com/" in an S3 image URL using a provided regex.

  Args:
      url (str): The S3 image URL.
      regex (str): The regular expression to match the desired string.

  Returns:
      str: The extracted string, or None if no match is found.
  """

  match = re.search(regex, url)
  if match:
    return match.group(1)
  else:
    return None

# Example usage with the provided URL and regex
regex = r".*\/([^\/]+\/[^\/]+)$"  # Assuming you want everything after "amazonaws.com/"
        
s3_client = boto3.client('s3', region_name='ap-south-1')
        

def extract_text_from_image(image_path):
    reader = easyocr.Reader(['en'])  # Add other languages if needed
    print(f'image path: {image_path}')
    s3_key_name = extract_string_after_amazonaws(image_path, regex)

    # Set expiration time for the pre-signed URL (e.g., 300 seconds)
    expiration = 300
    presigned_url = s3_client.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket_name, 'Key': s3_key_name},
        ExpiresIn=expiration
    )
    results = reader.readtext(presigned_url)

    # Initialize an empty list to store texts with high confidence
    high_confidence_text = []

    # Iterate through the results
    for (bbox, text, prob) in results:
        if prob > 0.8:  # Check if the confidence score is greater than 0.8
            # Append the text to the list
            high_confidence_text.append(text)
    
    print(f'high_confidence_text {high_confidence_text}')
    what_user_wants = what_user_wants_chain.invoke({"input": high_confidence_text})
    return what_user_wants
