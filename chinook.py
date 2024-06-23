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

db_uri = "postgresql://postgres:d9q4Juye$e@synydb.crae42w04nzr.us-east-1.rds.amazonaws.com:5432/postgres"
db = SQLDatabase.from_uri(db_uri, sample_rows_in_table_info=3)
# db = SQLDatabase.from_uri("sqlite:///syny.db", sample_rows_in_table_info=3)

examples = [
    {
        "input": "Quais dispositivos fazemos coleta?", 
        "query": "SELECT distinct type from device_twin_variable_histories"
    },
    {
        "input": "Qual o consumo total de gas?",
        "query": "SELECT SUM(CAST(value AS numeric)) FROM device_twin_variable_histories WHERE type = 'gas'"
    },
    {
        "input": "Qual o consumo total de agua em maio de 2023?",
        "query": r"""
            SELECT SUM(CAST(value AS numeric))
            FROM device_twin_variable_histories
            WHERE created_at between '2023-05-01' and '2023-05-31'
            AND type = 'water'
        """
    },
    {
        "input": "Agrupado por serviço, me diga qual mês e ano tive o consumo mais alto?",
        "query": r"""
            WITH MonthlyConsumption AS (
                SELECT type, to_char(created_at, 'YYYY-MM') AS month_year, SUM(CAST(value AS numeric)) AS total_consumption
                FROM public.device_twin_variable_histories
                WHERE value ~ '^[0-9]+(\.[0-9]+)?$'
                GROUP BY type, month_year
            ),
            MaxConsumption AS (
                SELECT type, month_year, MAX(total_consumption) AS max_consumption
                FROM MonthlyConsumption
                GROUP BY type, month_year
            )
            SELECT type, month_year, total_consumption
            FROM (
                SELECT type, month_year, total_consumption,
                    ROW_NUMBER() OVER (PARTITION BY type ORDER BY total_consumption DESC) AS rn
                FROM MonthlyConsumption
            ) AS ranked
            WHERE rn = 1;
        """
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

If the user does not specify the want the consumption in units, always assume it is in Brazilian Reais (R$)

Final answer should be fully translated to Portuguese (Brazil). Specify the format for numbers and currency:

In Brazil, numbers use a comma , as the decimal separator and a period . as the thousand separator.
Currency is typically represented with the symbol R$, placed before the number.

If the question does not seem related to the database or you don't know the answer, just return "I don't know" as the answer.

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

# # Example formatted prompt
# prompt_val = full_prompt.invoke(
#     {
#         "input": "Qual o consumo de gas esse mes?",
#         "top_k": 5,
#         "dialect": "PostgreSQL",
#         "agent_scratchpad": [],
#     }
# )

llm = ChatOpenAI(temperature=0, model="gpt-4o")

agent = create_sql_agent(
    llm=llm,
    db=db,
    prompt=full_prompt,
    verbose=True,
    agent_type="openai-tools",
)

response = agent.invoke({"input": "me diga qual mes e ano tive o consumo mais alto em 2024"})
print(response['output'])

response = agent.invoke({"input": "agora agrupe por serviço"})
print(response['output'])