import os
from uuid import uuid4
import ast


unique_id = uuid4().hex[0:8]



from langsmith import Client
from datetime import datetime

from langchain import hub
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, FewShotChatMessagePromptTemplate
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts.prompt import PromptTemplate
from langchain.agents import Tool
from langchain.tools import BaseTool, tool
from typing import Union, Optional
import itertools
import time
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
import re
from datetime import date
import uuid
from datetime import date



client = Client()

llm = ChatOpenAI(temperature = 0.0)

#importing embedding model here 

model_name = 'text-embedding-ada-002'

embed = OpenAIEmbeddings(
    model = model_name
)

index_name = 'finance-tracking-5'

from pinecone import Pinecone
pc = Pinecone(api_key='818d4111-8da6-4e85-9c18-03ac23d98b4d')

index = pc.Index(index_name)
index.describe_index_stats()

#testing embeddings here

texts = [
    'this is the first chunk of text',
    'then another second chunk of text is here'
]

res = embed.embed_documents(texts)
len(res), len(res[0])

# Using SQL Database for agent utility sql database for agent utility
import sqlite3
from langchain_community.utilities import SQLDatabase

sql_database = SQLDatabase.from_uri("sqlite:///staging-db.db")
print(sql_database.dialect)
print(sql_database.get_usable_table_names())
response = sql_database.run("SELECT * FROM expenditure_details")
print(response)



#creating few shots prompt for the chain

expenditure_examples = [
    {"today_date": "1998/10/23", "input": "26", "output": """{"Amount Spend": 26, "Purpose": "", paid_to : "", date_of_expenditure:"1998/10/23" }"""},
    {"today_date": "1998/10/23", "input": "dinner yesterday", "output": """{"Amount Spend": "", "Purpose": Dinner, paid_to: "", date_of_expenditure:"1998/10/22"}"""},
    {"today_date": "1998/10/23", "input": "32 sutta", "output": """{"Amont Spend": 32, "Purpose": sutta, paid_to: "", date_of_expenditure:"1998/10/23"}"""},
    {"today_date": "1998/10/23", "input": "what is india", "output": """{"Amont Spend": "", "Purpose": "", paid_to: "", date_of_expenditure:"1998/10/23"}"""},
    {"today_date": "1998/10/23", "input": "what is 2+2", "output": """{"Amont Spend": "", "Purpose": "", paid_to:"", date_of_expenditure:"1998/10/23"}"""},
    {"today_date": "1998/10/23", "input": "300 lunch meghna biryani", "output": """{"Amont Spend": "300", "Purpose": "lunch", paid_to:"meghna biryani", date_of_expenditure:"1998/10/23"}}"""},
    {"today_date": "1998/10/23", "input": "dominos pizza 320 yesterday", "output": """{"Amont Spend": "320", "Purpose": "pizza", paid_to:"dominos", date_of_expenditure:"1998/10/22"}"""},
    {"today_date": "1998/10/23", "input": "470 oct 13", "output": """{"Amont Spend": "470", "Purpose": "", paid_to:"", date_of_expenditure:"1998/10/13"}"""},
    {"today_date": "1998/10/23", "input": "lunch on 20th oct", "output": """{"Amont Spend": "", "Purpose": "lunch", paid_to:"", date_of_expenditure:"1998/10/20"}"""},
    {"today_date": "1998/10/23", "input": "pizza 320 yesterday", "output": """{"Amont Spend": "320", "Purpose": "pizza", paid_to:"", date_of_expenditure:"1998/10/22"}"""}

    


]

expenditure_example_prompt = ChatPromptTemplate.from_messages(
    [
        ("human", "{input} and todays date is {today_date}"),
        ("ai", "{output}")
    ]
)

expenditure_few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=expenditure_example_prompt,
    examples=expenditure_examples,
)

# prompt for  expenditure chain
system_prompt_to_get_expenditure_details = """You are an Assistant. Humans send messages to you to keep track of their daily expenditures.\
Extract four points from the message:\
1. Amount Spend\
2. Purpose of money spend\
3. To whom money is paid\
4. date of expenditure\
How to find date of expenditure?\
Check user message and date on which user is updating and figure out date after. Keep your response in YYYY-MM-DD format\
that. date of expenditure cannot be after date on which user is updating\
If you didn't find any of the above point in message, don't make it by yourself. Clearly pass empty value for that data point\
"""

prompt_to_get_expenditure_details = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt_to_get_expenditure_details),
        # MessagesPlaceholder(variable_name="chat_history"),
        expenditure_few_shot_prompt,
        ("human", "{input} and user is updating on {today_date}"),
    ]
)


# Define your parser for output.
class expenditureDetails(BaseModel):
    amount_paid: str = Field(description="how much amount paid")
    purpose: str = Field(description="why the amount is paid")
    paid_to: str = Field(description="where the amount is paid")
    date_of_expenditure: str = Field(description="Date when the amount is spent")

parser = JsonOutputParser(pydantic_object=expenditureDetails)

prompt_to_get_expenditure_details.messages[2].prompt = PromptTemplate(
    template="Answer the user query.\n{format_instructions}\n{input}\n and user is updating on {today_date}\n",
    input_variables=["input", "today_date"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)


expenditure_details_chain = prompt_to_get_expenditure_details | llm | parser


#creating chain to extract category of expenditure
system_prompt_to_extract_category = """ You have to find out the category in which below input lies\
You can choose one category from below mentioned categories. Do not think any category by yourself.\
1. EMI
2. Loan
3. Food
4. Commute
5. Travel
6. Bills/Recharge/Subscription/Maintainace
7. Grocery
8. Education
9. Savings
10. Chai, Cigrattes, Sutta
11. Maid Payment
12. Hobbies
13. Pets
14. Rent
16. Medical 
17. Fuel/Gas
18. Miscellanious
19. Party
20. Health and Fitness

Give your answer in one word
"""

prompt_to_get_expenditure_category = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt_to_extract_category),
        # MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ]
)

expenditure_category_chain = prompt_to_get_expenditure_category | llm | StrOutputParser()


#what user wants chain

system_prompt_to_what_user_wants_chain = """ You have to find out the why user is sending message to you.\
There can be two purpose
1. save_expenditure
2. get_expenditure_insights
Give you answer in one word.
"""

prompt_to_get_what_user_wants = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt_to_what_user_wants_chain),
        # MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ]
)

what_user_wants_chain = prompt_to_get_what_user_wants | llm | StrOutputParser()

what_user_wants_chain.invoke({"input": "70 pav bhaji"})

#Creating SQL Agent below to give insights on database
from langchain_community.agent_toolkits import create_sql_agent
sql_agent_executor = create_sql_agent(llm, db=sql_database, agent_type="openai-tools", verbose=True)


def extract_details_from_agent_input(agent_input:str):
  """
  Extracts the user message and id from a given text string.

  Args:
    text: The text string to extract from.

  Returns:
    A dictionary containing the extracted user message and id, or None if not found.
  """

  # Extract the user message and id using regular expressions
  match = re.search(r"qwerty = (\{[^\}]+\}) and id = (\{[^\}]+\}) and date = (\{[^\}]+\})", agent_input)

  # Extract the captured groups (the values between curly braces)
  user_message = match.group(1).strip("{}")
  id_value = match.group(2).strip("{}")
  today_date = match.group(3).strip("{}")
  return {"user_message": user_message, "id": id_value, "today_date": today_date}



import random


@tool
async def saveExpenditure(agent_input: str) -> str:
    "Use this to save expenditure , One input is required [agent_input]"
    # agent_input format : "um = {input} and id = {id}"
    agent_input = extract_details_from_agent_input(agent_input)
    print(agent_input['id'])
    response = expenditure_details_chain.invoke({"input":agent_input['user_message'], "today_date": agent_input['today_date']})
    response['category'] = expenditure_category_chain.invoke({"input":response['purpose']})
    #check if date_of_expenditure is of future date        
    if response["amount_paid"] == "" or response["purpose"] == "":
        return "Wrong message or incomplete details, we can only help you with your expenditure tracking" 
    else:
        #save in vector database
        response_string = str(response)
        embed_response = embed.embed_documents([response_string])
        embed_user_message = embed.embed_documents([agent_input['user_message']])
        vector_id_user_message = str(uuid.uuid4())
        vector_id_response = str(uuid.uuid4())
        current_timestamp = int(time.time())
        index.upsert(
            vectors = [
                {
                    "id": vector_id_user_message,
                    "values": embed_user_message[0],
                    "metadata": {'text': agent_input['user_message'], 'messageType': "HumanMessage", "time": current_timestamp}
                },
                {
                    "id": vector_id_response,
                    "values": embed_response[0],
                    "metadata": {'text': response_string ,  'messageType': "AIMessage", "time": current_timestamp}
                }

            ],
            namespace=agent_input['id']
       )
        #saving in sql db
        today = date.today()
        print(today)
        sql_database.run(
                   f"""INSERT INTO expenditure_details (user_id, amount_paid, purpose, paid_to, category, date_of_expenditure, created_at)\
                     VALUES ({agent_input['id']}, {response["amount_paid"]}, '{response["purpose"]}',\
                     '{response["paid_to"]}','{response["category"]}','{response["date_of_expenditure"]}','{today}');"""
                 )

    return response


@tool
async def getExpenditureInsights(agent_input: str) -> str:
    "Use this to get insights on expenditure, one input is required [agent_input]"
    agent_input = extract_details_from_agent_input(agent_input)
    print(agent_input)
    sql_agent_input = f"my query is `{agent_input['user_message']}` and my id is `{agent_input['id']}`, give me answer not sql query"
    sql_agent_response = sql_agent_executor.invoke({"input": sql_agent_input})
    return sql_agent_response


@tool
async def whatUserWants(agent_input: str) -> str:
    "Use this tool to find out the purpose of why human have messaged you [agent_input]"
    agent_input_extracted = extract_details_from_agent_input(agent_input) #to get agent_input_extracted['user_message'] for below use
    response = what_user_wants_chain.invoke({"input" : agent_input_extracted['user_message']})
    return f'Use {response} with input "{agent_input}"'


tools = [whatUserWants,saveExpenditure,getExpenditureInsights]

# Get the prompt to use - you can modify this!
prompt = hub.pull("hwchase17/openai-tools-agent")
prompt.messages[0].prompt.template = "You are a helpful assistant, pass human input as\
it is to whatUserWants tool and take action accordingly. Use Indian Rupees are currency if needed"
# print(prompt.messages) -- to see the prompt
agent = create_openai_tools_agent(
    llm.with_config({"tags": ["agent_llm"]}), tools, prompt
)
agent_executor = AgentExecutor(agent=agent, tools=tools).with_config(
    {"run_name": "Agent"}
)




from datetime import date

async def run_agent(user_message: str, id: str):
    today = date.today()
    agent_input = f'qwerty = {{{user_message}}} and id = {{{id}}} and date = {{{today}}}'

    async for chunk in agent_executor.astream({"input": agent_input}):
        if "actions" in chunk:
            for action in chunk["actions"]:
                if action.tool == "whatUserWants":
                    yield "Figuring out the purpose of your message\n"
                elif action.tool == "saveExpenditure":
                    yield "You want to update your expenditure details\n"
                else:
                    yield "You are looking for insights on your expenditure\n"
                
        if "output" in chunk:
            yield f'Final Output: {chunk["output"]}\n'





async def expenditure_data(id: str):
    """
    Extracts all records matching the given ID from the 'expenditure_data' table in the `staging-db.db` SQLite database.
    """

    if not id:
        raise ValueError("ID parameter cannot be missing or empty.")

    try:
        # Assuming sql_database has an async method to get a connection
        query = f"SELECT * FROM expenditure_details WHERE user_id = {id}"
        print(query)
        # Ensure parameters are passed as a tuple to prevent SQL injection
        rows = sql_database.run(query)

        # Assuming 'response' is the string you received
        response = rows

        # Safely convert the string representation of the list to an actual list of tuples
        records_tuples = ast.literal_eval(response)

        # Define the column names based on your schema
        column_names = ["user_id", "amount_paid", "purpose", "paid_to", "category", "date_of_expenditure", "created_at", "created_at_timestamp"]

        # Convert each tuple to a dictionary using column names as keys
        records_dicts = [dict(zip(column_names, record)) for record in records_tuples]

        sorted_records = sorted(records_dicts, key=lambda x: x["created_at_timestamp"], reverse=True)

        # Calculate total amount spent today
        today = datetime.now().date()
        total_spent_today = sum(record["amount_paid"] for record in sorted_records if datetime.strptime(record["created_at"], "%Y-%m-%d").date() == today)
        # Prepare the final response
        response = {
            "records": sorted_records,
            "total_spent_today": total_spent_today
        }

        return response

    except Exception as e:
        raise RuntimeError(f"Error retrieving expenditure data: {e}") from e


