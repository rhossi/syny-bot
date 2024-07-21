import boto3
from botocore.exceptions import ClientError
import os
import json
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# configuration
class BaseConfig(ABC):
    def __init__(self) -> None:
        load_dotenv()

        self.ENVIRONMENT = self.get_env('ENVIRONMENT') or 'prod'
        self.DB_URI = self.get_env('DATABASE_URI')
        self.LLM_MODEL = self.get_env('LLM_MODEL')
        self.APP_PORT = self.get_env('APP_PORT')
        self.REDIS_URL = self.get_env('REDIS_URL')
        self.TWILIO_AUTH_TOKEN = self.get_env('TWILIO_AUTH_TOKEN')
        self.TWILIO_ACCOUNT_SID = self.get_env('TWILIO_ACCOUNT_SID')
        self.AWS_SECRET_NAME = self.get_env('AWS_SECRET_NAME')
        self.AWS_REGION_NAME = self.get_env('AWS_REGION_NAME')
        self.TWILIO_FROM_NUMBER = self.get_env('TWILIO_FROM_NUMBER')
        self.OPENAI_API_KEY = self.get_env('OPENAI_API_KEY')
        
    def is_dev(self) -> bool:
        return False
        # return self.ENVIRONMENT == 'dev'
    
    def get_env(self, key: str) -> str:
        return os.getenv(key) if self.is_dev() else self.external_get_env(key)

    @abstractmethod
    def external_get_env(self, key: str) -> str:
        pass

class AWSConfig(BaseConfig):
    def __init__(self, secret_name, region_name) -> None:
        self.secret_name = secret_name
        self.region_name = region_name
        super().__init__()

    def external_get_env(self, key: str) -> str:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=self.region_name
        )

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=self.secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e

        secret_dict = json.loads(get_secret_value_response['SecretString'])

        return secret_dict.get(key,'not found')