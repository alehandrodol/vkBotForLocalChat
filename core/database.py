from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://umjvupqexundpj:8a7d37dceeb35a512ea4af29d08ce73b1a309071429c2b802bdd52d4ff33af59@ec2-54-216-17-9.eu-west-1.compute.amazonaws.com/d2t1hi986qmt4u"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    return SessionLocal()
