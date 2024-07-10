import os
import logging
import random
import re
from typing import Dict, Any

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from repository import Repository

# Configuration
class Config:
    DB_URI = os.getenv('DATABASE_URI', "postgresql://postgres:d9q4Juye$e@synydb.crae42w04nzr.us-east-1.rds.amazonaws.com:5432/postgres")
    LLM_MODEL = "gpt-4o"
    PORT = 8080

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize components
llm = ChatOpenAI(temperature=0, model=Config.LLM_MODEL)
repository = Repository(Config.DB_URI)
db = SQLDatabase.from_uri(Config.DB_URI, sample_rows_in_table_info=3)

# Load prompts
validate_question_prompt = PromptTemplate.from_file('prompts/validate_question.txt')
build_sql_prompt = PromptTemplate.from_file('prompts/build_sql.txt')
summary_prompt = PromptTemplate.from_file('prompts/summary.txt')
help_prompt = PromptTemplate.from_file('prompts/help.txt')

app = Flask(__name__)

def respond(message: str) -> str:
    response = MessagingResponse()
    response.message(message)
    return str(response)

def random_default_response() -> str:
    formal_responses = [
        "Não sou capaz de fornecer assistência para esse assunto. Para descobrir como posso ajudar, me pergunte: Como você pode me ajudar?"
    ]
    return random.choice(formal_responses)

def respond_with_ai(phone_number: str, question: str) -> str:
    previous_question = ''
    previous_datapoints = ''

    try:
        user_info = repository.find_user_by_phone(phone_number)
        logger.info(f"User info: {user_info}")

        logger.info("Validating question")
        chain = validate_question_prompt | llm
        response = chain.invoke(input={"question": question, "previous_question": previous_question})
        logger.info(f"Validation response: {response}")

        match response.content:
            case "INVALID_QUESTION":
                return respond(random_default_response())
            case "VALID_QUESTION":
                return handle_valid_question(question, previous_datapoints)
            case "VALID_HELP_QUESTION":
                return handle_help_question(user_info)
            case "VALID_SQL_QUESTION":
                return handle_sql_question(question, user_info)
            case _:
                return respond(random_default_response())
    except Exception as e:
        logger.error(f"Error in respond_with_ai: {e}")
        return respond("Desculpe, ocorreu um erro. Por favor, tente novamente mais tarde.")

def handle_valid_question(question: str, previous_datapoints: str) -> str:
    logger.info("Handling valid question")
    chain = summary_prompt | llm
    response = chain.invoke(input={"question": question, "datapoints": previous_datapoints})
    return respond(response.content)

def handle_help_question(user_info: Dict[str, Any]) -> str:
    logger.info("Handling help question")
    chain = help_prompt | llm
    response = chain.invoke(input={"customer_name": user_info["customer_name"]})
    return respond(response.content)

def handle_sql_question(question: str, user_info: Dict[str, Any]) -> str:
    logger.info("Handling SQL question")
    chain = build_sql_prompt | llm
    response = chain.invoke(input={"question": question, "customer_ids": user_info['customer_ids']})
    sql_query = response.content

    try:
        datapoints = db.run(sql_query)
        chain = summary_prompt | llm
        response = chain.invoke(input={"question": question, "datapoints": datapoints})
        summary_result = response.content

        repository.save_interaction(
            question_asked=question,
            sql_query_generated=sql_query,
            sql_query_result=datapoints,
            summary_result=summary_result
        )

        return respond(summary_result)
    except Exception as e:
        logger.error(f"Error executing SQL query: {e}")
        return respond("Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.")

@app.route('/message', methods=['POST'])
def reply():
    message = request.form.get('Body', '').lower()
    from_ = request.form.get('From', '')
    phone_number = re.search(r"\+?\d+", from_)

    if message and phone_number:
        logger.info(f"Received message: {message} from: {phone_number.group()}")
        return respond_with_ai(phone_number.group(), message)
    else:
        return respond("Desculpe, não foi possível processar sua mensagem.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)