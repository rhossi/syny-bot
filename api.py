import os
import logging
import random
import re
from typing import Dict, Any
from datetime import datetime, timedelta
import redis
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
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
from datetime import datetime, timedelta, timezone

# Configuration
class Config:
    DB_URI = os.getenv('DATABASE_URI', "postgresql://postgres:d9q4Juye$e@synydb.crae42w04nzr.us-east-1.rds.amazonaws.com:5432/postgres")
    LLM_MODEL = "gpt-4o"
    PORT = 8080
    REDIS_URL = "redis://clustercfg.synybot-cache.c6qmed.use1.cache.amazonaws.com:6379"
    # REDIS_URL = "redis://localhost:6379/0"

redis_client = redis.Redis(host='clustercfg.synybot-cache.c6qmed.use1.cache.amazonaws.com', decode_responses=True, ssl=True, port=6379, db=0)

# Setup logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# Initialize components
llm = ChatOpenAI(temperature=0, model=Config.LLM_MODEL)
repository = Repository(Config.DB_URI)
db = SQLDatabase.from_uri(Config.DB_URI, sample_rows_in_table_info=3)

# Load prompts
# validate_question_prompt = PromptTemplate.from_file('prompts/validate_question.txt')
# build_sql_prompt = PromptTemplate.from_file('prompts/build_sql.txt')
# summary_prompt = PromptTemplate.from_file('prompts/summary.txt')
# help_prompt = PromptTemplate.from_file('prompts/help.txt')

app = Flask(__name__)

def respond(message: str) -> str:
    response = MessagingResponse()
    response.message(message)
    return str(response)
      
@tool
def get_water_consumption(customer_id, start_date, end_date):
	"""Get the water consumption for a specific customer between two dates.

	Args:
		customer_id: The unique identifier of the customer.
		start_date: The start date of the period.
		end_date: The end date of the period.
	"""
    # Database connection parameters
	db_params = {
		"dbname": "postgres",
		"user": "postgres",
		"password": "d9q4Juye$e",
		"host": "synydb.crae42w04nzr.us-east-1.rds.amazonaws.com",
		"port": "5432"
	}

    # SQL query
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
		# Establish a connection to the database
		conn = psycopg2.connect(**db_params)
		
		# Create a cursor object
		cur = conn.cursor()
		
		# Execute the query
		cur.execute(query.format(
			customer_id=sql.Literal(customer_id),
			start_date=sql.Literal(start_date),
			end_date=sql.Literal(end_date)
		))
		
		# Fetch all results
		results = cur.fetchall()
		
		# Print results
		print(f"Water consumption from {start_date} to {end_date}:")
		
	except (Exception, psycopg2.Error) as error:
		print("Error while connecting to PostgreSQL", error)

	finally:
		# Close the database connection
		if conn:
			cur.close()
			conn.close()
			print("PostgreSQL connection is closed")

	return results


tools = [get_water_consumption]
    
# def respond_with_ai(phone_number: str, question: str) -> str:
#     previous_question = ''
#     previous_datapoints = ''

#     try:
#         user_info = repository.find_user_by_phone(phone_number)
#         logger.info(f"User info: {user_info}")

#         logger.info("Validating question")
#         chain = validate_question_prompt | llm
#         response = chain.invoke(input={"question": question, "previous_question": previous_question})
#         logger.info(f"Validation response: {response}")

#         match response.content:
#             case "INVALID_QUESTION":
#                 return respond(random_default_response())
#             case "VALID_QUESTION":
#                 return handle_valid_question(question, previous_datapoints)
#             case "VALID_HELP_QUESTION":
#                 return handle_help_question(user_info)
#             case "VALID_SQL_QUESTION":
#                 return handle_sql_question(question, user_info)
#             case _:
#                 return respond(random_default_response())
#     except Exception as e:
#         logger.error(f"Error in respond_with_ai: {e}")
#         return respond("Desculpe, ocorreu um erro. Por favor, tente novamente mais tarde.")

# def handle_valid_question(question: str, previous_datapoints: str) -> str:
#     logger.info("Handling valid question")
#     chain = summary_prompt | llm
#     response = chain.invoke(input={"question": question, "datapoints": previous_datapoints})
#     return respond(response.content)

# def handle_help_question(user_info: Dict[str, Any]) -> str:
#     logger.info("Handling help question")
#     chain = help_prompt | llm
#     response = chain.invoke(input={"customer_name": user_info["customer_name"]})
#     return respond(response.content)

# def handle_sql_question(question: str, user_info: Dict[str, Any]) -> str:
#     logger.info("Handling SQL question")
#     chain = build_sql_prompt | llm
#     response = chain.invoke(input={"question": question, "customer_ids": user_info['customer_ids']})
#     sql_query = response.content

#     try:
#         datapoints = db.run(sql_query)
#         chain = summary_prompt | llm
#         response = chain.invoke(input={"question": question, "datapoints": datapoints})
#         summary_result = response.content

#         repository.save_interaction(
#             question_asked=question,
#             sql_query_generated=sql_query,
#             sql_query_result=datapoints,
#             summary_result=summary_result
#         )

#         return respond(summary_result)
#     except Exception as e:
#         logger.error(f"Error executing SQL query: {e}")
#         return respond("Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.")

def process_message(phone_number: str, message: str) -> str:
    user_info = repository.find_user_by_phone(phone_number)
    customer_ids = user_info['customer_ids']
	
    if customer_ids is None:
        return "Desculpe, não encontramos o usuário associado a este número de telefone. Por favor entre em contato com o suporte."
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant that helps users with their questions about resource consumption."
            "\n\nSystem time: {time}"
            "\n\nSystem customer_id: {customer_id}"),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(time=datetime.now(timezone.utc).isoformat()).partial(customer_id=customer_ids)
    print(customer_ids)
    # Create RedisChatMessageHistory
    message_history = RedisChatMessageHistory(url=Config.REDIS_URL, ttl=5*60, session_id=phone_number)

    # Create ConversationBufferMemory with Redis backend
    memory = ConversationBufferMemory(chat_memory=message_history, memory_key="chat_history", return_messages=True)

    agent = create_tool_calling_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, memory=memory)

    result = agent_executor.invoke({"input": message})
    return result['output']

@app.route('/message', methods=['POST'])
def reply():
    message = request.form.get('Body', '').lower()
    from_ = request.form.get('From', '')
    phone_number_match = re.search(r"\+?\d+", from_)
    
    response = ''
    if message and phone_number_match:
        phone_number = phone_number_match.group()

        # logger.info(f"Received message: {message} from: {phone_number.group()}")
        response = process_message(phone_number, message)
    else:
        response = "Desculpe, não encontramos o usuário associado a este número de telefone. Por favor entre em contato com o suporte."
    
    return respond(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)