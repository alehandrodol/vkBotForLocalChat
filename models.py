from sqlalchemy import Column, Integer, String, Date, sql, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from core.database import Base


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    today_pdr = Column(Integer)
    who_is_fucked = Column(Integer)
    pdr_date = Column(Date)
    year_pdr = Column(Integer)
    year_pdr_num = Column(Integer)
    active_vote = Column(Integer, default=0)
    start_time = Column(DateTime)
    votes_counter = Column(Integer)
    for_user_vote = Column(Integer)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('groups.id'), primary_key=True, unique=False)
    firstname = Column(String)
    lastname = Column(String)
    pdr_num = Column(Integer)
    fucked = Column(Integer)
    rating = Column(Integer)
    pdr_of_the_year = Column(Integer)
    group = relationship(Group)
