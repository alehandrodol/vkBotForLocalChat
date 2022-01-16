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

    def __str__(self) -> str:
        return f"Instanse from table groups:\n" \
               f"id: {self.id}; name: {self.name}, today_pdr: {self.today_pdr}, who_is_fucked: {self.who_is_fucked}, " \
               f"pdr_date: {self.pdr_date},\nyear_pdr: {self.year_pdr}, year_pdr_num: {self.year_pdr_num},\n" \
               f"active_vote: {self.active_vote}, start_time: {self.start_time}, votes_counter: {self.votes_counter}, "\
               f"for_user_votes: {self.for_user_vote}.\n" \
               f"----------------------------------------------------------------------------------------------------\n"


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

    def __str__(self) -> str:
        return f"Instanse from table users:\n" \
               f"id: {self.id}, chat_id: {self.chat_id}, firstname: {self.firstname}, lastname: {self.lastname},\n" \
               f"pdr_num: {self.pdr_num}, fucked: {self.fucked}, rating: {self.rating}, " \
               f"pdr_of_the_year: {self.pdr_of_the_year}.\n" \
               f"---------------------------------------------------------------------------------------------------\n"