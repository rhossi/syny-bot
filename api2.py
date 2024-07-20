import os
import re
from typing import List
from datetime import datetime, timedelta, timezone
import redis
from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from repository import Repository
from langchain.agents import AgentExecutor
from langchain_core.tools import tool
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
import psycopg2
from psycopg2 import sql
import nltk
from config import AWSConfig

SECRET_NAME = "prod/syny-bot"
AWS_REGION_NAME = "us-east-1"

config = AWSConfig(secret_name=SECRET_NAME, region_name=AWS_REGION_NAME)

app = FastAPI()
nltk.download('punkt', quiet=True)

# Initialize components
llm = ChatOpenAI(temperature=0, model=config.LLM_MODEL)
redis_client = redis.from_url(url=config.REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
db = SQLDatabase.from_uri(config.DB_URI, sample_rows_in_table_info=3)
repository = Repository(config.DB_URI)

def respond(message: str) -> str:
    response = MessagingResponse()
    response.message(message)
    return str(response)

@tool
def get_water_consumption(customer_id: str, start_date: str, end_date: str):
    """Get the water consumption for a specific customer between two dates."""

    query = sql.SQL("""
    WITH period_values AS (
        SELECT 
        MIN(CAST(value AS DECIMAL(15,2))) AS period_start_value,
        MAX(CAST(value AS DECIMAL(15,2))) AS period_end_value
        FROM public.device_twin_variable_histories
        WHERE "type" = 'water'
        AND customer_id = {customer_id}
        AND created_at >= {start_date}::date
        AND created_at < {end_date}::date + INTERVAL '1 day'
    )
    SELECT 
        CASE 
        WHEN period_end_value >= period_start_value THEN period_end_value - period_start_value
        ELSE period_end_value  -- Assume a reset occurred if end value is less than start value
        END AS total_consumption
    FROM period_values;
    """)

    results = []
    try:
        with psycopg2.connect(config.DB_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(query.format(
                    customer_id=sql.Literal(customer_id),
                    start_date=sql.Literal(start_date),
                    end_date=sql.Literal(end_date)
                ))
                results = cur.fetchall()
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)

    return results

tools = [get_water_consumption]

def chunk_message(message: str, max_chars: int = 1500) -> List[str]:
    """
    Chunk a long message semantically into smaller parts, each not exceeding max_chars.
    
    Args:
    message (str): The input message to be chunked.
    max_chars (int): The maximum number of characters per chunk (default is 1600).
    
    Returns:
    List[str]: A list of message chunks.
    """
    if len(message) <= max_chars:
        return [message]
    
    sentences = nltk.sent_tokenize(message)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:  # +1 for space
            current_chunk += (" " if current_chunk else "") + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

async def send_chunked_message(result: str, phone_number: str):
    chunks = chunk_message(result)
    for i, chunk in enumerate(chunks, 1):
        prefix = f"[{i}/{len(chunks)}]: " if len(chunks) > 1 else ""
        message = prefix + chunk
        twilio_client.messages.create(
            to=f'whatsapp:{phone_number}',
            from_=f'whatsapp:{setup['twilio']['from_number']}',
            body=message
        )
        print(f"Sent chunk {i}/{len(chunks)} to user")

def process_message(phone_number: str, message: str) -> str:
    user_info = repository.find_user_by_phone(phone_number)
    customer_ids = user_info['customer_ids']
    
    if customer_ids is None:
        return "Desculpe, não encontramos o usuário associado a este número de telefone. Por favor entre em contato com o suporte."
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant that helps users with their questions about resource consumption.  Use narrative format, no bullets. Be concise, objective, limit your responses to 1599 characters."
            "\n\nSystem time: {time}"
            "\n\nSystem customer_id: {customer_id}"),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(time=datetime.now(timezone.utc).isoformat()).partial(customer_id=customer_ids)
    print(customer_ids)
    
    message_history = RedisChatMessageHistory(url=config.REDIS_URL, ttl=5*60, session_id=phone_number)
    memory = ConversationBufferMemory(chat_memory=message_history, memory_key="chat_history", return_messages=True)
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, memory=memory)

    result = agent_executor.invoke({"input": message})
    return result['output']

@app.post("/message", response_class=PlainTextResponse)
async def reply(Body: str = Form(...), From: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    message = Body.lower()
    phone_number_match = re.search(r"\+?\d+", From)
    
    if message and phone_number_match:
        phone_number = phone_number_match.group()
        response = process_message(phone_number, message)
        background_tasks.add_task(send_chunked_message, response, phone_number)
        return ""
    else:
        return respond("Desculpe, não encontramos o usuário associado a este número de telefone. Por favor entre em contato com o suporte.")

def send_completion_message(result: str, phone_number: str):
    print("send_completion_message")
    twilio_client.messages.create(to=f'whatsapp:{phone_number}', from_='whatsapp:+14155238886', body=result)
    print(f"Sending completion message to user: {result}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(config.APP_PORT))