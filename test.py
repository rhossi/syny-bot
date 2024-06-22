from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

sql_prompt = PromptTemplate.from_template(
    "using the table historic_data (customer_id text, type text, value float, created_at datetime) convert the user question {question} into a sql query"
)

summarizer_prompt = PromptTemplate.from_template(
    """Given the question and sql query and the results, summarize in a clear and objective sentence to the user

        Question: {question}
        SQL Query: {sql}
    """
)

llm = ChatOpenAI()

sql_chain = sql_prompt | llm | StrOutputParser()
summarizer_chain = summarizer_prompt | llm | StrOutputParser()
chain = ({"sql": sql_chain}
         | RunnablePassthrough.assign(summary=summarizer_chain))


result = chain.invoke({"question": "qual mes teve o maior consumo de gas?"})
print(result['question'])
print(result['query'])
print(result['summary'])