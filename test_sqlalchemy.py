import sqlalchemy as db
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

db_uri = "postgresql://postgres:d9q4Juye$e@synydb.crae42w04nzr.us-east-1.rds.amazonaws.com:5432/postgres"

engine = db.create_engine(db_uri)
Session = sessionmaker(bind=engine)
session = Session()

class Interaction(Base):
    __tablename__ = 'interactions'
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_asked = Column(String)
    question_prompt = Column(String)
    question_result = Column(String)
    sql_query_generated = Column(String)
    sql_query_prompt = Column(String)
    sql_query_result = Column(String)
    summary_prompt = Column(String)
    summary_result = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

new_interaction = Interaction(
    question_asked="What is the capital of France?",
    question_prompt="Please tell me the capital of France.",
    question_result="The capital of France is Paris.",
    sql_query_generated="SELECT capital FROM countries WHERE name = 'France';",
    sql_query_prompt="Generate a SQL query to find the capital of France.",
    sql_query_result="Paris",
    summary_prompt="Summarize the information about France's capital.",
    summary_result="Paris is the capital city of France."
)

try:
    session.add(new_interaction)
    session.commit()
    print(f"New interaction created with ID: {new_interaction.id}")

    interactions = session.query(Interaction).all()

    for interaction in interactions:
        print(f"ID: {interaction.id}, Question Asked: {interaction.question_asked}")
except Exception as e:
    print(f"An error occurred: {e}")
    session.rollback()
finally:
    session.close()



