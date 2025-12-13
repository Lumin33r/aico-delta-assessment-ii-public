import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Database Configuration
    # TODO: Configure database connection string
    DATABASE_URI = os.getenv('DATABASE_URI')
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    LEX_BOT_ID = os.getenv('LEX_BOT_ID')
    LEX_BOT_ALIAS_ID = os.getenv('LEX_BOT_ALIAS_ID')
    
    # TODO: Add more configuration as needed