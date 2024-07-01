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
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
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

### help prompt
help_prompt = PromptTemplate.from_file('prompts/help.txt')

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
class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    name = Column(String)
    credential_id = Column(Integer, ForeignKey('credentials.credential_id'))
    credential = relationship("Credential", back_populates="user")

class Credential(Base):
    __tablename__ = 'credentials'
    credential_id = Column(Integer, primary_key=True)
    phone = Column(String)
    user = relationship("User", back_populates="credential")

class UserCustomer(Base):
    __tablename__ = 'user_customer'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    customer_id = Column(Integer)
    user = relationship("User")

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

def find_user_by_phone(phone):
    query = session.query(User.name, UserCustomer.customer_id).\
    join(Credential, User.credential_id == Credential.credential_id).\
    join(UserCustomer, User.user_id == UserCustomer.user_id).\
    filter(Credential.phone == phone)

    customer_name = ''
    customer_ids = []

    results = query.all()

    for name, customer_id in results:
        if customer_name == '':
            customer_name = name
        
        customer_ids.append(customer_id)

    return { "customer_name": customer_name, "customer_ids": customer_ids}
    

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

def respond_with_ai(question):
    previous_question = ''
    previous_datapoints = ''
    final_response = ''

    user_info = find_user_by_phone('+14043045909')
    logger.info(user_info)

    logger.info("validating question")
    chain = validate_question_prompt | llm
    response = chain.invoke(input={"question":question, "previous_question": previous_question})
    logger.info(response)

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
        case "VALID_HELP_QUESTION":
            logger.info("VALID_HELP_QUESTION")
            logger.info("## summary")
            chain = help_prompt | llm
            response = chain.invoke(input={"customer_name":user_info["customer_name"]})
            summary_result = response.content
            logger.info(response)
            final_response = respond(summary_result)
        case "VALID_SQL_QUESTION":
            logger.info("# VALID_SQL_QUESTION")
            logger.info("## building SQL")
            chain = build_sql_prompt | llm
            response = chain.invoke(input={"question":question, "customer_ids":user_info['customer_ids']})
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
    from_ = request.form.get('From')

    if message:
        logger.info("got message: " + message)
        logger.info("from: " + from_)

        return respond_with_ai(message)
    

if __name__ == "__main__":
    port = 8080
    app.run(host="0.0.0.0", port=port, debug=True)