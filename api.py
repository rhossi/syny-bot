import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)

db = SQLDatabase.from_uri("sqlite:///syny.db", sample_rows_in_table_info=3)

examples = [
    {
        "input": "Quais dispositivos fazemos coleta?", 
        "query": "SELECT distinct type from historic_data"
    },
    {
        "input": "Qual o consumo total de gas?",
        "query": "SELECT SUM(value) FROM historic_data WHERE type = 'gas'",
    },
    {
        "input": "Qual o consumo total de agua em maio de 2023?",
        "query": """
            SELECT SUM(value)
            FROM historic_data
            WHERE strftime('%Y-%m', created_at) = '2023-05'
            AND type = 'water';
        """,
    },
    {
        "input": "Agrupado por serviço, me diga qual mês e ano tive o consumo mais alto?",
        "query": """
            WITH MonthlyConsumption AS (
                SELECT type, strftime('%Y-%m', created_at) AS month_year, SUM(value) AS total_consumption
                FROM historic_data
                GROUP BY type, month_year
            ),
            MaxConsumption AS (
                SELECT month_year, MAX(total_consumption) AS max_consumption
                FROM MonthlyConsumption
                GROUP BY month_year
                ORDER BY max_consumption DESC
                LIMIT 1
            )
            SELECT DISTINCT h.type, strftime('%Y-%m', h.created_at) AS month_year, SUM(h.value) AS total_consumption
            FROM historic_data h
            JOIN MaxConsumption m ON strftime('%Y-%m', h.created_at) = m.month_year
            GROUP BY h.type, month_year;
        """,
    }
]

example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")

example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples,
    OpenAIEmbeddings(),
    FAISS,
    k=5,
    input_keys=["input"],
)

system_prefix = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the given tools. Only use the information returned by the tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database or you don't know the answer, just return "I don't know" as the answer.

Final answer should be fully translated to Portuguese (Brazil).

Here are some examples of user inputs and their corresponding SQL queries:"""

few_shot_prompt = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=example_prompt,
    prefix=system_prefix,
    suffix="",
    input_variables=["input", "top_k", "dialect"],
)

full_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(prompt=few_shot_prompt),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

# Example formatted prompt
prompt_val = full_prompt.invoke(
    {
        "input": "Qual o consumo de gas esse mes?",
        "top_k": 5,
        "dialect": "SQLite",
        "agent_scratchpad": [],
    }
)

llm = ChatOpenAI(temperature=0)

agent = create_sql_agent(
    llm=llm,
    db=db,
    prompt=full_prompt,
    verbose=False,
    agent_type="openai-tools",
)

app = Flask(__name__)

DEFAULT_RESPONSE = "Não sei a resposta. Por favor entre em contato com sac@syny.com.br"

def respond_with_ai(input):
    response = agent.invoke({"input": input})

    if response and response['output']:
        return respond(response['output'])
    else:
        return respond(DEFAULT_RESPONSE)

def respond(message):
    response = MessagingResponse()
    response.message(message)
    return str(response)

@app.route('/message', methods=['POST'])
def reply():
    message = request.form.get('Body').lower()
    if message:
        return respond_with_ai(message)
    

if __name__ == "__main__":
    port = 8080
    app.run(host="0.0.0.0", port=port)