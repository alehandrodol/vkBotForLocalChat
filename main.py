import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, VkBotMessageEvent
from vk_api.utils import get_random_id

from random import choice, randint

from core.Base import Base
from core.database import engine, get_db

from models import Group, User

from sqlalchemy.orm import Session
from datetime import datetime

from typing import Union, List

from json import loads

import pytz


class Bot:
    def __init__(self):
        # Base.metadata.drop_all(bind=engine)
        # Tables creation
        Base.metadata.create_all(bind=engine)

        # Auth
        self.vk_session = vk_api.VkApi(
            token='e870b89da7be761fae34bcbd531d1530941bcc0e85feb26a15f65f09ded05dbb77eded17d0b58963c34e3')
        self.vk = self.vk_session.get_api()
        self.params = self.vk.groups.getLongPollServer(group_id=209871225)

        with open("./DataBases/groups_data.json", 'r') as f:
            db: Session = get_db()
            read = f.read()
            data_list = loads(read)['values']
            for line in data_list:
                record_group: Group = db.query(Group).filter(Group.id == line[0]).first()
                if record_group is None:
                    record_group = Group(
                        id=line[0],
                        name=line[1],
                        today_pdr=line[2],
                        who_is_fucked=line[3],
                        pdr_date=line[4],
                        year_pdr=line[5],
                        year_pdr_num=line[6]
                    )
                    self.commit(db=db, inst=record_group)
            db.close()

        with open("./DataBases/users_data.json", 'r') as f:
            db: Session = get_db()
            read = f.read()
            data_list = loads(read)['values']
            for line in data_list:
                record_user: User = db.query(User).filter(User.id == line[0], User.chat_id == line[1]).first()
                if record_user is None:
                    record_user = User(
                        id=line[0],
                        chat_id=line[1],
                        firstname=line[2],
                        lastname=line[3],
                        pdr_num=line[4],
                        fucked=line[5]
                    )
                    self.commit(db=db, inst=record_user)
            db.close()

    @staticmethod
    def commit(db: Session, inst: Union[Group, User]):
        db.add(inst)
        db.commit()
        db.refresh(inst)

    def get_random_user(self, users: list[dict]) -> tuple[list[dict], dict]:
        # Choosing random user from list
        num = randint(0, len(users)-1)
        user_id = users[num]['member_id']
        while user_id < 0:
            num = randint(0, len(users) - 1)
            user_id = users[num]['member_id']

        users.pop(num)
        # Getting more info about user
        user = self.vk.users.get(user_ids=user_id)
        return users, user[0]

    def make_empty_record_in_groups(self, event: VkBotMessageEvent, db: Session) -> Group:
        chat_name = self.vk.messages.getConversationsById(
            peer_ids=event.message['peer_id'])['items'][0]['chat_settings']['title']
        record_group = Group(
            id=event.chat_id,
            name=chat_name,
            today_pdr=None,
            who_is_fucked=None,
            year_pdr=None,
            year_pdr_num=datetime.today().year
        )
        self.commit(db=db, inst=record_group)
        return record_group

    def make_empty_record_in_users(self, event: VkBotMessageEvent, db: Session, user_id: int) -> User:
        user = self.vk.users.get(user_ids=user_id)[0]
        record: User = User(
            id=user_id,
            chat_id=event.chat_id,
            firstname=user['first_name'],
            lastname=user['last_name'],
            pdr_num=0,
            fucked=0
        )
        self.commit(db=db, inst=record)
        return record

    def random_pdr(self, db: Session, event: VkBotMessageEvent) -> None:
        # Getting all users from chat
        users = self.vk.messages.getConversationMembers(peer_id=event.message['peer_id'])

        users, user = self.get_random_user(users['items'])

        # Getting record from table
        record_group: Group = db.query(Group).filter(Group.id == event.chat_id).first()

        # Is record exist
        if record_group is None:  # Make record if not
            record_group = self.make_empty_record_in_groups(event=event, db=db)

        moscow_zone = pytz.timezone("Europe/Moscow")
        # Check if we had already chosen pdr user today
        if datetime.now(tz=moscow_zone).date() == record_group.pdr_date:
            user = self.vk.users.get(user_ids=record_group.today_pdr)[0]
            self.send_message(event.chat_id,
                              text=f'Вы же знаете, сегодня пидор - '
                                   f'[id{user["id"]}|{user["first_name"]} {user["last_name"]}]')
            fucked = self.vk.users.get(user_ids=record_group.who_is_fucked, name_case='acc')[0]
            self.send_message(event.chat_id,
                              text=f"А трахает он - "
                                   f"[id{fucked['id']}|{fucked['first_name']} {fucked['last_name']}]")
        # If not
        else:
            users, fucked = self.get_random_user(users)
            fucked_temp = self.vk.users.get(user_ids=fucked['id'], name_case='acc')[0]

            record_group.today_pdr = user['id']
            record_group.pdr_date = datetime.now(tz=moscow_zone).date()
            record_group.who_is_fucked = fucked['id']
            self.commit(db=db, inst=record_group)

            record_user: User = db.query(User).filter(User.id == user['id'], User.chat_id == event.chat_id).first()
            if record_user is None:
                record_user = self.make_empty_record_in_users(event=event, db=db, user_id=user['id'])

            record_fucked: User = db.query(User).filter(
                User.id == fucked['id'], User.chat_id == event.chat_id).first()
            if record_fucked is None:
                record_fucked = self.make_empty_record_in_users(event=event, db=db, user_id=fucked['id'])
            record_fucked.fucked += 1
            self.commit(db=db, inst=record_fucked)

            record_user.pdr_num += 1
            self.commit(db=db, inst=record_user)

            self.send_message(chat_id=event.chat_id,
                              text=f'Сегодня пидор - '
                                   f'[id{user["id"]}|{user["first_name"]} {user["last_name"]}]')
            self.send_message(event.chat_id,
                              text=f"А трахает он - "
                                   f"[id{fucked['id']}|{fucked_temp['first_name']} {fucked_temp['last_name']}]")

    def statistics(self, db: Session, event: VkBotMessageEvent, option: bool) -> None:
        record_group: Group = db.query(Group).filter(Group.id == event.chat_id).first()
        if record_group is None:
            self.make_empty_record_in_groups(event=event, db=db)
        if option:
            users_records: List[User] = db.query(User).order_by(User.pdr_num.desc()). \
                filter(User.chat_id == event.chat_id).all()
        else:
            users_records: List[User] = db.query(User).order_by(User.fucked.desc()). \
                filter(User.chat_id == event.chat_id).all()
        # Getting all users from chat
        users = self.vk.messages.getConversationMembers(peer_id=event.message['peer_id'])
        users_ids_in_conversation = [user['member_id'] for user in users['items'] if user['member_id'] > 0]
        user_ids_in_db: List[int] = [user.id for user in users_records]
        if len(users_ids_in_conversation) > len(user_ids_in_db):
            for user_id in users_ids_in_conversation:
                if user_id not in user_ids_in_db:
                    record_user = self.make_empty_record_in_users(event=event, db=db, user_id=user_id)
                    users_records.append(record_user)
        text = ''
        for record_user in users_records:
            count_num = record_user.pdr_num if option else record_user.fucked
            if count_num <= 0:
                continue
            text += f'[id{record_user.id}|' \
                    f'{record_user.firstname} ' \
                    f'{record_user.lastname}] {"имел титул" if option else "зашёл не в ту дверь"} ' \
                    f'{count_num} ' \
                    f'{"раза" if count_num % 10 in [2, 3, 4] and count_num not in [12, 13, 14] else "раз"}\n'
        self.send_message(chat_id=event.chat_id, text=text)

    def pdr_of_the_year(self, db: Session, event: VkBotMessageEvent) -> None:
        record_group: Group = db.query(Group).filter(Group.id == event.chat_id).first()
        if record_group is None:
            record_group = self.make_empty_record_in_groups(event=event, db=db)
        if record_group.year_pdr is not None and datetime.today().year == record_group.year_pdr_num:
            user = self.vk.users.get(user_ids=record_group.year_pdr)[0]
            self.send_message(event.chat_id,
                              text=f"Пидр этого года уже извстен, это - "
                                   f"[id{user['id']}|{user['first_name']} {user['last_name']}]")
        else:
            users = self.vk.messages.getConversationMembers(peer_id=event.message['peer_id'])

            users, user = self.get_random_user(users)
            record_group.year_pdr = user['id']
            self.commit(db, record_group)
            self.send_message(event.chat_id,
                              text=f"Я нашёл главного пидора этого года, это - "
                                   f"[id{user['id']}|{user['first_name']} {user['last_name']}]")

    def send_message(self, chat_id, text) -> None:
        self.vk.messages.send(
            key=(self.params['key']),
            server=(self.params['server']),
            ts=(self.params['ts']),
            random_id=get_random_id(),
            message=text,
            chat_id=chat_id
        )

    def suka_all(self, event: VkBotMessageEvent) -> None:
        messages = [f"Я [id{event.message['from_id']}|тебе] сейчас allну по ебалу",
                    f"Ты чего охуел, [id{event.message['from_id']}|Пидор], блять???"]
        self.send_message(event.chat_id,
                          text=choice(messages))

    def personal_stats(self, event: VkBotMessageEvent, db: Session) -> None:
        record_user: User = db.query(User). \
            filter(User.id == event.message['from_id'], User.chat_id == event.chat_id).first()
        self.send_message(chat_id=event.chat_id,
                          text=f"[id{record_user.id}|Ты] был титулован {record_user.pdr_num} "
                               f"{'раза' if record_user.id % 10 in [2, 3, 4] and record_user.id not in [12, 13, 14] else 'раз'}\n"
                               f"и зашёл не в тот gym {record_user.fucked} "
                               f"{'раза' if record_user.fucked % 10 in [2, 3, 4] and record_user.fucked not in [12, 13, 14] else 'раз'}\n")

    def listen(self):

        longpoll = VkBotLongPoll(self.vk_session, 209871225)

        # listen for events
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                session: Session = get_db()
                message: str = event.message['text']
                randoms = ['рандом', 'кто пидор?', 'рандомчик', 'пидор дня']
                year = ['годовалый', 'пидор года']
                pdr_stats = ['титулы', 'кол-во пидоров', 'статистика титулы', 'статистика']
                fucked_stats = ['статистика пассивных']
                if event.from_chat:
                    if message.lower() in randoms:
                        self.random_pdr(db=session, event=event)
                    elif message.lower() in year:
                        self.pdr_of_the_year(db=session, event=event)
                    elif message.lower() in pdr_stats:
                        self.statistics(db=session, event=event, option=True)
                    elif message.lower() == "моя статистика":
                        self.personal_stats(event=event, db=session)
                    elif message.lower() in fucked_stats:
                        self.statistics(db=session, event=event, option=False)
                    elif '@all' in message.lower():
                        self.suka_all(event)
                    elif message == 'команды':
                        text = ""
                        text += f"выбор пидора дня: {', '.join(randoms)};\n " \
                                f"выбор пидора года: {', '.join(year)};\n" \
                                f"показ статистики титулов: {', '.join(pdr_stats)};\n" \
                                f"показ статистики пассивных: {', '.join(fucked_stats)};\n" \
                                f"хочешь чтоб тебя послали нахуй? Попробуй написать all;" \
                                f"Чтобы узнать статистику только по тебе, используй 'моя статистика'."

                        self.send_message(event.chat_id,
                                          text=text)
                session.close()


if __name__ == '__main__':
    bot = Bot()
    bot.listen()
