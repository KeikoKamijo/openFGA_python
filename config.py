import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from openfga_sdk.client import OpenFgaClient, ClientConfiguration

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FGA_API_URL = os.getenv('FGA_API_URL', 'http://localhost:8080')
    FGA_STORE_ID = os.getenv('FGA_STORE_ID')
    FGA_MODEL_ID = os.getenv('FGA_MODEL_ID')
    AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
    AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
    AUTH0_API_AUDIENCE = os.getenv('AUTH0_API_AUDIENCE')
    DEFAULT_USER_EMAIL = os.getenv('DEFAULT_USER_EMAIL', 'alice@example.com')
    DEFAULT_USER_ROLE = os.getenv('DEFAULT_USER_ROLE', 'guest')

# SQLAlchemy setup
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False} if "sqlite" in Config.SQLALCHEMY_DATABASE_URI else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# OpenFGA client setup
configuration = ClientConfiguration(
    api_url=Config.FGA_API_URL,
    store_id=Config.FGA_STORE_ID,
    authorization_model_id=Config.FGA_MODEL_ID,
)
fga_client = OpenFgaClient(configuration)

# Database dependency
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()