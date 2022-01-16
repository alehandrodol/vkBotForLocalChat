import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#SQLALCHEMY_DATABASE_URL = os.environ.get("LOCAL_DB_URL")
SQLALCHEMY_DATABASE_URL = "postgres://uncrmqmakbcslr:c781a0fb47f5e832591bb83d2ca0322a929316ae94e98297343d8ac9805f3337@ec2-34-249-49-9.eu-west-1.compute.amazonaws.com:5432/dd7qgns69c3tnf"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    return SessionLocal()
