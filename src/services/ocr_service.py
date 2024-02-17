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


# os.environ["AWS_SECRET_ACCESS_KEY"] = "24/MRj8Fxtsn3mYcg0xkMA2OyXddDRz2isD+Ywp4"
# os.environ["AWS_ACCESS_KEY_ID"] = "AKIAZQ3DN323XRZLSQ4N"

unique_id = uuid4().hex[0:8]

# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_PROJECT"] = "pt-authorized-prefix-30"
# os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
# os.environ["LANGCHAIN_API_KEY"] = "ls__36c6855495a940e7b0e04101249b4745"  # Update to your API key

# Used by the agent in this tutorial
# os.environ["OPENAI_API_KEY"] = "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"

client = Client()




llm = ChatOpenAI(temperature = 0.0)


#what user wants chain

caption_text_from_image_system_prompt = """ You have given some important piece of information in array of jumbeled words. \
This information is important for user to save\
You have to recreate information and why user wants to save it. Keep your answer shorts.
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
    print(image_path)
    s3_key_name = extract_string_after_amazonaws(image_path, regex)

    # Set expiration time for the pre-signed URL (e.g., 300 seconds)
    expiration = 300
    print(s3_key_name)
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
    
    print(high_confidence_text)
    what_user_wants = what_user_wants_chain.invoke({"input": high_confidence_text})
    return what_user_wants
