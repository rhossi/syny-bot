from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
import sqlalchemy as db
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from twilio.twiml.messaging_response import MessagingResponse
from flask import Flask, request
import sys
import logging
import random

# llm setup
llm = ChatOpenAI(temperature=0, model="gpt-4o")

### loading prompts

### validate question first
validate_question_prompt = PromptTemplate.from_file('prompts/validate_question.txt')

### build sql prompt
build_sql_prompt = PromptTemplate.from_file('prompts/build_sql.txt')

### summary prompt
summary_prompt = PromptTemplate.from_file('prompts/summary.txt')

# db setup
Base = declarative_base()

db_uri = "postgresql://postgres:d9q4Juye$e@synydb.crae42w04nzr.us-east-1.rds.amazonaws.com:5432/postgres"
db = SQLDatabase.from_uri(db_uri, sample_rows_in_table_info=3)

engine = create_engine(db_uri)
Session = sessionmaker(bind=engine)
session = Session()

# loggin setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# app
class Interaction(Base):
    __tablename__ = 'interactions'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_asked = Column(String)
    sql_query_generated = Column(String)
    sql_query_result = Column(String)
    summary_result = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def save_interaction(**kwargs):
    try:
        new_interaction = Interaction(
            question_asked=kwargs["question_asked"],
            sql_query_generated=kwargs["sql_query_generated"],
            sql_query_result=kwargs["sql_query_result"],
            summary_result=kwargs["summary_result"]
        )

        session.add(new_interaction)
        session.commit()
        logger.info(f"New interaction created - {kwargs}")
    except Exception as e:
        logger.error(f"Error creating new interaction: {e}")
        session.rollback()
    finally:
        session.close()

app = Flask(__name__)

def random_default_response():
    funny_responses = [
        "Eita, peguei um bug mental aqui! 🐛🧠 Melhor chamar os exterminadores de problemas em sac@syny.com.br!",
        "Opa, tô mais perdido que pinguim no deserto! 🐧🏜️ Dá um toque no sac@syny.com.br, eles são melhores que GPS!",
        "Puts, deu tela azul no meu cérebro! 💻💥 Chama os hackers do bem em sac@syny.com.br pra um resgate!",
        "Vixe, tô mais enrolado que fone de ouvido no bolso! 🎧🌀 Desenrola essa com a galera do sac@syny.com.br!",
        "Epa, meu banco de dados tá mais vazio que geladeira de estudante! 🍽️ Abastece com o pessoal do sac@syny.com.br!",
        "Opa, tô mais confuso que gato em banheira! 🐱🛁 Joga a boia pro sac@syny.com.br, eles sabem nadar nessas águas!",
        "Caramba, me sinto um peixe tentando andar de bicicleta! 🐠🚲 Pedala até o sac@syny.com.br pra uma ajudinha!",
        "Poxa, meu código tá mais bagunçado que quarto de adolescente! 🧑‍🦱💻 Chama a faxina tech do sac@syny.com.br!",
        "Opa, tô mais travado que porta de banco! 🚪🏦 Destranca essa com a chave-mestra do sac@syny.com.br!",
        "Eita, meu processador tá fumegando! 🔥💻 Chama os bombeiros digitais do sac@syny.com.br pra apagar esse incêndio!"
    ]

    return random.choice(funny_responses)

def respond_with_ai(input):
    previous_question = ''
    previous_datapoints = ''
    final_response = ''
    question = input

    customer_id = "00000000-6581-f04c-75f9-3601bf8ba2fe"

    logger.info("validating question")
    chain = validate_question_prompt | llm
    response = chain.invoke(input={"question":question, "previous_question": previous_question})
    
    match response.content:
        case "INVALID_QUESTION":
            logger.info("INVALID_QUESTION")
            final_response = respond(random_default_response())
        case "VALID_QUESTION":
            logger.info("VALID_QUESTION")
            logger.info("## summary")
            chain = summary_prompt | llm
            response = chain.invoke(input={"question":question, "datapoints":previous_datapoints})
            summary_result = response.content
            logger.info(response)
            final_response = respond(summary_result)
        case "VALID_SQL_QUESTION":
            logger.info("# VALID_SQL_QUESTION")
            logger.info("## building SQL")
            chain = build_sql_prompt | llm
            response = chain.invoke(input={"question":question, "customer_id":customer_id})
            sql_query = response.content
            sql_query_generated = sql_query

            logger.info(sql_query)

            logger.info("## running sql query")
            datapoints = db.run(sql_query)
            previous_datapoints = datapoints
            logger.info(datapoints)

            logger.info("## summary")
            chain = summary_prompt | llm
            response = chain.invoke(input={"question":question, "datapoints":datapoints})
            summary_result = response.content
            logger.info(response)

            final_response = respond(summary_result)

            save_interaction(
                question_asked=question, 
                sql_query_generated=sql_query_generated,
                sql_query_result=datapoints,
                summary_result=summary_result
            )

    logger.debug("returning final response: " + final_response)
    return final_response

def respond(message):
    response = MessagingResponse()
    response.message(message)
    return str(response)

@app.route('/message', methods=['POST'])
def reply():
    message = request.form.get('Body').lower()
    
    if message:
        logger.debug("got message: " + message)
        print(message)
        return respond_with_ai(message)
    

if __name__ == "__main__":
    port = 8080
    app.run(host="0.0.0.0", port=port, debug=True)