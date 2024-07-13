import sqlalchemy as db
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
import logging
import sys

Base = declarative_base()

class Repository:

    def __init__(self, db_uri):
        # loggin setup
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        engine = create_engine(db_uri)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def save_interaction(self, **kwargs):
        try:
            new_interaction = Interaction(
                question_asked=kwargs["question_asked"],
                sql_query_generated=kwargs["sql_query_generated"],
                sql_query_result=kwargs["sql_query_result"],
                summary_result=kwargs["summary_result"]
            )

            self.session.add(new_interaction)
            self.session.commit()
            self.logger.info(f"New interaction created - {kwargs}")
        except Exception as e:
            self.logger.error(f"Error creating new interaction: {e}")
            self.session.rollback()
        finally:
            self.session.close()

    def find_user_by_phone(self, phone):
        print(phone)
        query = self.session.query(User.name, UserCustomer.customer_id).\
        join(Credential, User.credential_id == Credential.credential_id).\
        join(UserCustomer, User.user_id == UserCustomer.user_id).\
        filter(Credential.phone == phone)
        print(query)
        
        customer_name = ''
        customer_ids = []

        results = query.all()

        for name, customer_id in results:
            if customer_name == '':
                customer_name = name
            
            customer_ids.append(customer_id)

        return { "customer_name": customer_name, "customer_ids": customer_ids}
    

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
