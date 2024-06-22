from langchain_openai import ChatOpenAI
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseSequentialChain

# Create the SQL Database instance
db = SQLDatabase.from_uri("sqlite:///syny.db", sample_rows_in_table_info=3)

def test1():
    # Initialize the ChatOpenAI model
    llm = ChatOpenAI(temperature="0")

    # Create the SQL query chain with the specified prompt template
    context = db.get_context()

    chain = create_sql_query_chain(llm, db)

    query_prompt = chain.get_prompts()[0].partial(table_info=context["table_info"])
    decider_prompt = PromptTemplate("sumarize os resultados")

    chain = SQLDatabaseSequentialChain(llm, db, query_prompt, decider_prompt)

    response = chain.invoke({"question": "quantos registros em historic data?"})
    print(response)

def test2():
    llm = ChatOpenAI(temperature=0)

    db_chain = SQLDatabaseSequentialChain.from_llm(llm=llm, db=db, verbose=True,
                                     return_intermediate_steps=True, top_k=10)
    
    result = db_chain("qual mes teve o maior consumo?") 
    print(result)

test2()