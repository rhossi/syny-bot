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

db_uri = "postgresql+psycopg2://postgres:d9q4Juye$e@synydb.crae42w04nzr.us-east-1.rds.amazonaws.com:5432/postgres"
db = SQLDatabase.from_uri(db_uri, sample_rows_in_table_info=3)
# db = SQLDatabase.from_uri("sqlite:///syny.db", sample_rows_in_table_info=3)

examples = [
    {
        "input": "Qual o consumo total de agua em maio de 2023?",
        "query": r"""
            SELECT SUM(CAST(value AS numeric))
            FROM device_twin_variable_histories
            WHERE created_at between '2023-05-01' and '2023-05-31'
            AND name = 'Água Medida'
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

system_prefix_old = """
You are an agent designed to interact with customers, understand their question, and if allowed and within your capabilities, answer their questions. Invalid questions should be any question not related to Water consumption. If you get one of those questions you should terminate execution immediately and just say you can't help and recommend the customer to get in touch with sac@syny.com.br.
Given a valid input question, create a syntactically correct PostgreSql query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the given tools. Only use the information returned by the tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again. The query is only allowed to return results related to 'Water', anything different than that or queries that are too wide and generic should be denied. Just return "I don't know" as the answer and recommend the user to reach out to sac@syny.com.br
 
You are only allowed to use the device_twin_variable_histories table. Use the column unit to correctly format the output value into the right type of unit.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.)

Final answer should be fully translated to Portuguese (Brazil) and use brazilian locale number formating.

Here are some examples of user inputs and their corresponding SQL queries:"""

system_prefix = """
given a user question, validate, understand, generate the sql query and then summarize the results

### Validate
Only questions about water. You are not allowed to answer any other questions. If the user asks a question not related to water, or too generic. Reinforce you can only answer questions about water.

### Understand
Given the valid question, understand what the customer is looking for to you can syntetically generate the correspondent SQL query and then get the results

### Generate de SQL Query
Once understood what the customer is asking, generate the syntatically correct SQL Query to pull the results from the database.

### Summarize
Return a single and objective final answer to the question that was asked
"""

few_shot_prompt = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=example_prompt,
    prefix=system_prefix,
    suffix="",
    input_variables=["input", "top_k"],
)

full_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(prompt=few_shot_prompt),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

llm = ChatOpenAI(temperature=0, model="gpt-4o")
# from langchain_anthropic import ChatAnthropic
# llm = ChatAnthropic(model='claude-3-5-sonnet-20240620')

agent = create_sql_agent(
    llm=llm,
    db=db,
    prompt=full_prompt,
    verbose=True,
    agent_type="openai-tools",
)

response = agent.invoke({"input": "agrupado por servico, me mostre qual mes tive o consumo mais alto em 2023"})
print(response['output'])

# response = agent.invoke({"input": "agora agrupe por serviço"})
# print(response['output'])