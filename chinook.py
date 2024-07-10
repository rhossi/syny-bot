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
from repository import Repository
import sys
import logging

llm = ChatOpenAI(temperature=0, model="gpt-4o")

Base = declarative_base()

db_uri = "postgresql://postgres:d9q4Juye$e@synydb.crae42w04nzr.us-east-1.rds.amazonaws.com:5432/postgres"
db = SQLDatabase.from_uri(db_uri, sample_rows_in_table_info=3)

repository = Repository(db_uri)

engine = create_engine(db_uri)
Session = sessionmaker(bind=engine)
session = Session()

logger = logging.getLogger()
# logger.setLevel(logging.INFO)

# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.INFO)

# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

### loading prompts

### validate question first
validate_question_prompt = PromptTemplate.from_file('prompts/validate_question.txt')

### build sql prompt
build_sql_prompt = PromptTemplate.from_file('prompts/build_sql.txt')

### summary prompt
summary_prompt = PromptTemplate.from_file('prompts/summary.txt')

### help prompt
help_prompt = PromptTemplate.from_file('prompts/help.txt')

print("Enter text (press CTRL+C to exit):")

try:
    previous_question = ''
    previous_datapoints = ''
    question = ''

    while True:
        user_info = repository.find_user_by_phone("+14043045909")
        logger.info(user_info)

        question = input()

        logger.info("validating question")
        chain = validate_question_prompt | llm
        response = chain.invoke(input={"question":question, "previous_question": previous_question})
        
        match response.content:
            case "INVALID_QUESTION":
                logger.info("INVALID_QUESTION")
                continue
            case "VALID_QUESTION":
                logger.info("VALID_QUESTION")
                logger.info("## summary")
                chain = summary_prompt | llm
                response = chain.invoke(input={"question":question, "datapoints":previous_datapoints})
                summary_result = response.content
                logger.info(response)
            case "VALID_HELP_QUESTION":
                logger.info("VALID_HELP_QUESTION")
                logger.info("## summary")
                chain = help_prompt | llm
                response = chain.invoke(input={"customer_name":user_info["customer_name"]})
                summary_result = response.content
                logger.info(response)
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

                repository.save_interaction(
                    question_asked=question, 
                    sql_query_generated=sql_query_generated,
                    sql_query_result=datapoints,
                    summary_result=summary_result
                )

        previous_question = question
except KeyboardInterrupt:
    print("\nInput terminated by user.")
    sys.exit(0)