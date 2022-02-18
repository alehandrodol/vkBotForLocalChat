import re
import sys
import os

import vk_api

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, VkBotMessageEvent
from vk_api.utils import get_random_id

from service_funcs import my_random, get_group_record, get_user_record, make_vk_user_schema, \
    make_vk_message_schema, get_achieve_record, get_user_achieve_record, user_api, commit, find_word
from vote_waiting import auto_end_vote

from core.Base import Base
from core.database import engine, get_db

from models import Group, User, Achieves, UserAchieve
from schemas import VkUser, VkMessage

from sqlalchemy.orm import Session

import pytz
from datetime import datetime, timedelta

from typing import List, Union

from json import loads, dump

from subprocess import Popen, PIPE

from DataBases.last_messages import bot_last_message, chat_last_message


class Bot:
    def __init__(self):  # Bot start
        # Base.metadata.drop_all(bind=engine)
        # Tables creation
        Base.metadata.create_all(bind=engine)

        # Auth
        self.vk_session = vk_api.VkApi(
            token=os.environ.get("GROUP_TOKEN"))
        self.vk = self.vk_session.get_api()
        self.params = self.vk.groups.getLongPollServer(group_id=209871225)

        self.avoid_achieves = [6, 7]  # var for avoiding sending messages for achieves with these ids

        '''Two blocks of with is wor changing or creation data from json files'''
        with open("./DataBases/groups_data.json", 'r', encoding="utf8") as f:
            db: Session = get_db()
            read = f.read()
            data_list = loads(read)['values']
            for line in data_list:
                record_group: Group = get_group_record(line[0], db)
                if record_group is None:
                    record_group = Group(
                        id=line[0],
                        name=line[1],
                        today_pdr=line[2],
                        who_is_fucked=line[3],
                        pdr_date=line[4],
                        year_pdr=line[5],
                        year_pdr_num=line[6],
                        active_vote=line[7],
                        start_time=line[8],
                        votes_counter=line[9],
                        for_user_vote=line[10]
                    )
                    commit(db=db, inst=record_group)
            db.close()

        with open("./DataBases/users_data.json", 'r', encoding="utf8") as f:
            db: Session = get_db()
            read = f.read()
            data_list = loads(read)['values']
            for line in data_list:
                record_user: User = get_user_record(line[0], line[1], db)
                if record_user is None:
                    record_user = User(
                        id=line[0],
                        chat_id=line[1],
                        firstname=line[2],
                        lastname=line[3],
                        pdr_num=line[4],
                        fucked=line[5],
                        rating=line[6],
                        pdr_of_the_year=line[7]
                    )
                    commit(db=db, inst=record_user)
            db.close()

        with open("./DataBases/achieves_data.json", 'r', encoding="utf8") as f:
            db: Session = get_db()
            read = f.read()
            data_list = loads(read)['values']
            for line in data_list:
                record_achieve: Achieves = get_achieve_record(line[0], db)
                if record_achieve is None:
                    record_achieve = Achieves(
                        id=line[0],
                        name=line[1],
                        points=line[2],
                        is_available=line[3],
                        needed_repeats=line[4],
                        day_count_reachieve=line[5],
                        secs_to_reseting=line[6],
                    )
                    commit(db=db, inst=record_achieve)
            db.close()

        with open("./DataBases/Users_Achieves_data.json", 'r', encoding="utf8") as f:
            db: Session = get_db()
            read = f.read()
            data_list = loads(read)['values']
            for line in data_list:
                record_user_achieve: UserAchieve = get_user_achieve_record(line[0], line[1], line[2], db)
                if record_user_achieve is None:
                    record_user_achieve = UserAchieve(
                        user_id=line[0],
                        achieve_id=line[1],
                        chat_id=line[2],
                        last_date=line[3],
                        current_repeats=line[4],
                        is_got=line[5],
                        reachieve_date=line[6],
                        got_times=line[7]
                    )
                    commit(db=db, inst=record_user_achieve)
            db.close()

    def get_random_user(self, users: list[dict]) -> tuple[list[dict], VkUser]:
        """
        This func chooses random user from list

        :param users: must be a list of vk_user dicts

        :return: tuple(users, user) users: list of vk_user dicts, user: VkUser schema
        """
        num = my_random(len(users))
        user_id = users[num]['member_id']
        while user_id < 0:  # re-random if user is group
            num = my_random(len(users))
            user_id = users[num]['member_id']

        users.pop(num)
        # Getting more info about user from vk
        user = self.vk.users.get(user_ids=user_id)[0]
        user = make_vk_user_schema(user)
        return users, user

    def make_empty_record_in_groups(self, event: VkBotMessageEvent, db: Session) -> Group:
        """
        This function creates and pushes empty record for table 'groups' in DB

        :return: Group: ORM model for table groups
        """
        chat_name = self.vk.messages.getConversationsById(
            peer_ids=event.message['peer_id']
        )['items'][0]['chat_settings']['title']

        record_group = Group(
            id=event.chat_id,
            name=chat_name,
            today_pdr=None,
            who_is_fucked=None,
            year_pdr=None,
            year_pdr_num=datetime.today().year,
            active_vote=0,
            start_time=None,
            votes_counter=0,
            for_user_vote=None
        )
        commit(db=db, inst=record_group)
        return record_group

    def make_empty_record_in_users(self, event: VkBotMessageEvent, db: Session, user_id: int) -> User:
        """
        This function creates and pushes empty record for table 'users' in DB

        :return: User: ORM model for table users
        """
        user = self.vk.users.get(user_ids=user_id)[0]
        record: User = User(
            id=user_id,
            chat_id=event.chat_id,
            firstname=user['first_name'],
            lastname=user['last_name'],
            pdr_num=0,
            fucked=0,
            rating=0,
            pdr_of_the_year=0
        )
        commit(db=db, inst=record)
        return record

    def make_empty_record_in_users_achieves(self, event: VkBotMessageEvent, db: Session,
                                            user_id: int, achieve_id: int) -> UserAchieve:
        """
        This function creates and pushes empty record for table 'users_achieves' in DB

        :return: User: ORM model for table users_achieves
        """
        record: UserAchieve = UserAchieve(
            user_id=user_id,
            achieve_id=achieve_id,
            chat_id=event.chat_id,
            last_date=None,
            current_repeats=0,
            is_got=False,
            reachieve_date=None,
            got_times=0
        )
        commit(db, record)
        return record

    def random_pdr(self, db: Session, event: VkBotMessageEvent) -> None:
        """
        This function chooses a two random users from chat
        save this data into DB adds points for users and send message to chat
        what this program have chosen.
        However, this work only if this call of this function is first in given day, in another case this function
        will take information from DB

        :return: None (instead of return message in chat)
        """
        message: VkMessage = make_vk_message_schema(event.message)
        # Getting all users from chat
        users = self.vk.messages.getConversationMembers(peer_id=message.peer_id)

        users, user = self.get_random_user(users['items'])

        # Getting record from table
        record_group: Group = get_group_record(event.chat_id, db)

        moscow_zone = pytz.timezone("Europe/Moscow")
        # Check if we had already chosen pdr user today
        if datetime.now(tz=moscow_zone).date() == record_group.pdr_date:
            user = self.vk.users.get(user_ids=record_group.today_pdr)[0]
            user = make_vk_user_schema(user)

            self.send_message(event.chat_id,
                              text=f'Вы же знаете, сегодня пидор - '
                                   f'{user.first_name} {user.last_name}')
            fucked = self.vk.users.get(user_ids=record_group.who_is_fucked, name_case='acc')[0]
            fucked = make_vk_user_schema(fucked)
            self.send_message(event.chat_id,
                              text=f"А трахает он - "
                                   f"{fucked.first_name} {fucked.last_name}")
        # If not
        else:
            launch_user: User = get_user_record(message.from_id, event.chat_id, db)
            launch_user.rating += 25
            commit(db, launch_user)

            users, fucked = self.get_random_user(users)
            fucked_temp = self.vk.users.get(user_ids=fucked.id, name_case='acc')[0]
            fucked_temp = make_vk_user_schema(fucked_temp)

            record_group.today_pdr = user.id
            record_group.pdr_date = datetime.now(tz=moscow_zone).date()
            record_group.who_is_fucked = fucked.id
            commit(db=db, inst=record_group)

            record_user: User = get_user_record(user.id, event.chat_id, db)
            if record_user is None:
                record_user = self.make_empty_record_in_users(event=event, db=db, user_id=user.id)

            record_fucked: User = get_user_record(fucked.id, event.chat_id, db)
            if record_fucked is None:
                record_fucked = self.make_empty_record_in_users(event=event, db=db, user_id=fucked.id)
            record_fucked.fucked += 1
            record_fucked.rating += 50
            commit(db=db, inst=record_fucked)
            self.achieve_got(achieve_id=1, for_user=record_fucked.id, event=event, db=db)

            record_user.pdr_num += 1
            record_user.rating += 100
            commit(db=db, inst=record_user)
            self.achieve_got(achieve_id=1, for_user=record_user.id, event=event, db=db)

            self.send_message(chat_id=event.chat_id,
                              text=f'Сегодня пидор - '
                                   f'[id{user.id}|{user.first_name} {user.last_name}]')
            self.send_message(event.chat_id,
                              text=f"А трахает он - "
                                   f"[id{fucked.id}|{fucked_temp.first_name} {fucked_temp.last_name}]")
            self.send_picture(event=event)

    def statistics(self, db: Session, event: VkBotMessageEvent, option: int) -> None:
        """
        This function show statics from DB by given option
        :param db: Session for db
        :param event: event from chat
        :param option: this param defines what kind of stats we need to show
            1 - pdr_num stats
            2 - fucked stats
            3 - ratings stats
        :return: None (instead of return message in chat)
        """
        record_group: Group = get_group_record(event.chat_id, db)
        message: VkMessage = make_vk_message_schema(event.message)
        if record_group is None:
            self.make_empty_record_in_groups(event=event, db=db)
        if option == 1:
            users_records: List[User] = db.query(User).order_by(User.pdr_num.desc()). \
                filter(User.chat_id == event.chat_id).all()
        elif option == 2:
            users_records: List[User] = db.query(User).order_by(User.fucked.desc()). \
                filter(User.chat_id == event.chat_id).all()
        else:
            users_records: List[User] = db.query(User).order_by(User.rating.desc()). \
                filter(User.chat_id == event.chat_id).all()
        # Getting all users from chat
        users = self.vk.messages.getConversationMembers(peer_id=message.peer_id)

        # Next block is needed for check is DB has actual list of users if not add who are not there
        users_ids_in_conversation = [user['member_id'] for user in users['items'] if user['member_id'] > 0]
        user_ids_in_db: List[int] = [user.id for user in users_records]
        if len(users_ids_in_conversation) > len(user_ids_in_db):
            for user_id in users_ids_in_conversation:
                if user_id not in user_ids_in_db:
                    record_user = self.make_empty_record_in_users(event=event, db=db, user_id=user_id)
                    users_records.append(record_user)

        # Next block for configuration message text
        text = ''
        for record_user in users_records:
            if option == 3:
                if record_user.rating == 0:
                    continue
                text += f'{record_user.firstname} ' \
                        f'{record_user.lastname} ' \
                        f'имеет рейтинг пидора: {record_user.rating}\n'
            else:
                count_num = record_user.pdr_num if option == 1 else record_user.fucked
                if count_num <= 0:
                    continue
                text += f'{record_user.firstname} ' \
                        f'{record_user.lastname} {"имел титул" if option else "зашёл не в ту дверь"} ' \
                        f'{count_num} ' \
                        f'{"раза" if count_num % 10 in [2, 3, 4] and count_num not in [12, 13, 14] else "раз"}\n'
        self.send_message(chat_id=event.chat_id, text=text)

    def pdr_of_the_year(self, db: Session, event: VkBotMessageEvent) -> None:
        """
        This function check is pdr_of_the_year already known if not
        chooses new year_pdr and gives him rating points
        :return: None (instead of return message in chat)
        """
        record_group: Group = get_group_record(event.chat_id, db)
        message: VkMessage = make_vk_message_schema(event.message)
        if record_group is None:
            record_group = self.make_empty_record_in_groups(event=event, db=db)
        if record_group.year_pdr is not None and datetime.today().year == record_group.year_pdr_num:
            user = self.vk.users.get(user_ids=record_group.year_pdr)[0]
            self.send_message(event.chat_id,
                              text=f"Пидр этого года уже извстен, это - "
                                   f"[id{user['id']}|{user['first_name']} {user['last_name']}]")
        else:
            users = self.vk.messages.getConversationMembers(peer_id=message.peer_id)

            users, user = self.get_random_user(users['items'])
            record_user: User = get_user_record(user.id, event.chat_id, db)
            record_user.rating += 1000
            record_user.pdr_of_the_year += 1
            record_group.year_pdr = user.id
            commit(db, record_group)
            commit(db, record_user)
            self.send_message(event.chat_id,
                              text=f"Я нашёл главного пидора этого года, это - "
                                   f"[id{user.id}|{user.first_name} {user.last_name}]")

    def send_message(self, chat_id, text) -> None:
        """
        This func just configure message for vk method, it needs only
        chat_id and text for message, other params is taken from self
        """
        msg_id = get_random_id()
        self.vk.messages.send(
            key=(self.params['key']),
            server=(self.params['server']),
            ts=(self.params['ts']),
            random_id=msg_id,
            message=text,
            chat_id=chat_id
        )
        bot_last_message[chat_id] = msg_id

    def suka_all(self, db: Session, event: VkBotMessageEvent) -> None:
        """
        This function is called when someone write @all into chat
        main goal of func is to subtract points for this user and write funny message
        :return: None (instead of return message in chat)
        """
        message: VkMessage = make_vk_message_schema(event.message)
        launch_user: User = get_user_record(message.from_id, event.chat_id, db)
        launch_user.rating -= 5
        commit(db, launch_user)
        messages = [f"Я [id{message.from_id}|тебе] сейчас allну по ебалу",
                    f"Ты чего охуел, [id{message.from_id}|Пидор], блять???"]
        self.send_message(event.chat_id,
                          text=messages[my_random(len(messages))])

    def personal_stats(self, event: VkBotMessageEvent, db: Session) -> None:
        """Just take information from DB and distribute on the message text"""
        record_user: User = get_user_record(event.message['from_id'], event.chat_id, db)
        self.send_message(chat_id=event.chat_id,
                          text=f"[id{record_user.id}|Ты] был титулован {record_user.pdr_num} "
                               f"{'раза' if record_user.id % 10 in [2, 3, 4] and record_user.id not in [12, 13, 14] else 'раз'} "
                               f"и зашёл не в тот gym {record_user.fucked} "
                               f"{'раза' if record_user.fucked % 10 in [2, 3, 4] and record_user.fucked not in [12, 13, 14] else 'раз'}\n"
                               f"Твой рейтинг сейчас: {record_user.rating}\n"
                               f"Кол-во титулов 'Пидор года': {record_user.pdr_of_the_year}")

    def send_picture(self, event: VkBotMessageEvent) -> None:
        """
        Here is you can see the login into account for getting user access token
        after that we count photos in certain album and make random offset
        offset is like index for photo in this case
        and last action is taking photo id
        :return None (instead of return message in chat)
        """
        user_vk = user_api()

        counter = user_vk.photos.getAlbums(owner_id="-209871225", album_ids="282103569")["items"][0]["size"]
        offset = my_random(counter)
        photo_id = user_vk.photos.get(owner_id="-209871225", album_id="282103569", rev=True, count=1, offset=offset)["items"][0]["id"]

        self.vk.messages.send(
            key=(self.params['key']),
            server=(self.params['server']),
            ts=(self.params['ts']),
            random_id=get_random_id(),
            message="",
            chat_id=event.chat_id,
            attachment=f"photo-209871225_{photo_id}"
        )

    def send_gif(self, event: VkBotMessageEvent, index: int = None) -> None:
        """
        This function for sending random gif from docs in vk group.
        System of getting almost like in func 'send_picture', but
        using vk.docs.get type=3 means that type is 'gif'
        """
        user_vk = user_api()

        list_of_gifs = user_vk.docs.get(type=3, owner_id=-209871225)
        if index is None:
            index = my_random(list_of_gifs['count'])
        gif_id = list_of_gifs['items'][index]['id']
        self.vk.messages.send(
            key=(self.params['key']),
            server=(self.params['server']),
            ts=(self.params['ts']),
            random_id=get_random_id(),
            message="",
            chat_id=event.chat_id,
            attachment=f"doc-209871225_{gif_id}"
        )

    @staticmethod
    def send_data_to(proc, inp):
        proc.communicate(inp)

    def start_vote(self, db: Session, event: VkBotMessageEvent, option: int) -> None:
        """
        This function is called for starting vote:
            main goal is to write data into groups table about starting vote in current chat
            and of course sending message about it into chat
        :param db: Session
        :param event: VkBotMessageEvent
        :param option: This param defines + or - rating vote we are doing now
        """
        record_group: Group = get_group_record(event.chat_id, db)

        # This block for checking is voting ended or not
        moscow_zone = pytz.timezone("Europe/Moscow")
        now = datetime.now(tz=moscow_zone)
        is_time = (now - record_group.start_time.astimezone(moscow_zone)).seconds > 3600
        if is_time:
            auto_end_vote(db=db, group_id=event.chat_id, params=self.params, vk=self.vk)

        message: VkMessage = make_vk_message_schema(event.message)

        # This block for taking user id from message
        for_user = message.text
        for_user = int(re.search(r'[\d]{8,10}', for_user).group(0))

        if record_group.active_vote > 0:
            self.send_message(chat_id=event.chat_id, text="Уже есть запущенное голосование!")
            return

        with open("./DataBases/users.json", 'r') as f:
            read = f.read()
            read_data: dict = loads(read)

        users = self.vk.messages.getConversationMembers(peer_id=message.peer_id)
        read_data[f"{event.chat_id}"] = [user['member_id'] for user in users['items'] if user['member_id'] > 0 and user['member_id'] != message.from_id and user['member_id'] != for_user]

        with open("./DataBases/users.json", 'w') as f:
            dump(read_data, f)

        record_group.active_vote = 1 if option else 2
        moscow_zone = pytz.timezone("Europe/Moscow")
        record_group.start_time = datetime.now(tz=moscow_zone)
        record_group.votes_counter = 0
        record_group.for_user_vote = for_user
        commit(db, record_group)

        proc = Popen([sys.executable, "vote_waiting.py"], stdin=PIPE)
        proc.stdin.write((f"{event.chat_id}".encode('utf-8')))
        proc.stdin.close()

        self.send_message(chat_id=event.chat_id,
                          text=f"@all Началось голосование на {'+' if option else '-'}rep")

    def hand_end_vote(self, db: Session, event: VkBotMessageEvent):
        """This function forced termination of vote"""
        record_group: Group = get_group_record(event.chat_id, db)
        record_group.active_vote = 0
        commit(db=db, inst=record_group)
        self.send_message(chat_id=event.chat_id, text="Голосвание было отмененно.")

    def say_vote(self, db: Session, event: VkBotMessageEvent, option: bool) -> None:
        """
        This function add a vote into voting
        :param db: Session
        :param event: VkBotMessageEvent
        :param option: is needed for decision of vote 'for' or 'against' this voting
        """
        record_group: Group = get_group_record(event.chat_id, db)
        message: VkMessage = make_vk_message_schema(event.message)

        if record_group.active_vote == 0:
            self.send_message(chat_id=event.chat_id,
                              text=f"Сейчас нет активных голосований, но прошлое завершилось "
                                   f"{'успешно' if record_group.votes_counter > 0 else 'не успешно'}")
            return

        # This block for checking is voting ended or not
        moscow_zone = pytz.timezone("Europe/Moscow")
        now = datetime.now(tz=moscow_zone)
        is_time = (now - record_group.start_time.astimezone(moscow_zone)).seconds > 3600
        if is_time:
            auto_end_vote(db=db, group_id=event.chat_id, params=self.params, vk=self.vk)
            return

        with open("./DataBases/users.json", 'r') as f:
            read = f.read()
            read_data: dict = loads(read)

        li: list = read_data[f"{event.chat_id}"]
        print("Список доступных на голосование", li)
        print("Кто проголосовал", message.from_id)
        if message.from_id not in li:
            self.send_message(chat_id=event.chat_id,
                              text=f"[id{message.from_id}|Вы], не можете голосовать.")
            return

        if option:
            record_group.votes_counter += 1
        else:
            record_group.votes_counter -= 1

        # This block deletes user from voting
        li.remove(message.from_id)
        read_data[f"{event.chat_id}"] = li
        with open("./DataBases/users.json", 'w') as f:
            dump(read_data, f)

        commit(db, record_group)
        self.send_message(chat_id=event.chat_id,
                          text=f"[id{message.from_id}|Твой] голос записан.")

        # Check for early competition
        if abs(record_group.votes_counter) >= 7:
            auto_end_vote(db=db, group_id=event.chat_id, params=self.params, vk=self.vk)

    def vote_check(self, db: Session, event: VkBotMessageEvent) -> None:
        """This func is called by messages from chat for checking status of voting"""
        record_group: Group = get_group_record(event.chat_id, db)

        if record_group.active_vote == 0:
            self.send_message(chat_id=event.chat_id,
                              text=f"Сейчас нет активных голосований, но прошлое завершилось "
                                   f"{'успешно' if record_group.votes_counter > 0 else 'не успешно'}")
            return

        moscow_zone = pytz.timezone("Europe/Moscow")
        now = datetime.now(tz=moscow_zone)
        is_time = (now - record_group.start_time.astimezone(moscow_zone)).seconds > 3600
        if is_time:
            auto_end_vote(db=db, group_id=event.chat_id, params=self.params, vk=self.vk)
        else:
            record_user = get_user_record(record_group.for_user_vote, record_group.id, db)
            self.send_message(chat_id=event.chat_id,
                              text=f"Текущее голосование за то, чтобы "
                                   f"{'начислить' if record_group.active_vote == 1 else 'снять'} "
                                   f"50 рейтинга у [id{record_user.id}|{record_user.firstname}].\n"
                                   f"На данный момент перевес в "
                                   f"{'положительную' if record_group.votes_counter > 0 else 'отрицательную'} "
                                   f"сторону на {abs(record_group.votes_counter)}.\n"
                                   f"Голосование закончится через {60 - ((now - record_group.start_time.astimezone(moscow_zone)).seconds // 60)} минут")

    def achieve_got(self, achieve_id: int, for_user: int, event: VkBotMessageEvent, db: Session) -> Union[None, int]:
        """This functiom is always called when someone did any action for getting achieve"""

        record_achieve: Achieves = get_achieve_record(achieve_id, db)
        record_user: User = get_user_record(for_user, event.chat_id, db)
        record_user_achieve: UserAchieve = get_user_achieve_record(for_user, achieve_id, event.chat_id, db)

        status = 1

        if record_user_achieve is None:
            record_user_achieve = self.make_empty_record_in_users_achieves(event=event, db=db, user_id=for_user, achieve_id=achieve_id)

        moscow_zone = pytz.timezone("Europe/Moscow")
        now = datetime.now(tz=moscow_zone)
        if record_user_achieve.is_got:
            if record_user_achieve.reachieve_date is None or record_user_achieve.reachieve_date > now.date():
                print(f"Для пользователя {for_user} ачивка {achieve_id} не доступна")
                status = 0
                return status
            else:
                record_user_achieve.is_got = False
                record_user_achieve.reachieve_date = None
                record_user_achieve.current_repeats = 0

        if record_user_achieve.last_date is not None:
            if record_achieve.secs_to_reseting >= 86400:
                if (now.date() - record_user_achieve.last_date.date()).days > record_achieve.secs_to_reseting // 86400:
                    record_user_achieve.current_repeats = 0
            else:
                if (now - record_user_achieve.last_date.astimezone(pytz.utc)).seconds > record_achieve.secs_to_reseting:
                    record_user_achieve.current_repeats = 0

        record_user_achieve.current_repeats += 1
        record_user_achieve.last_date = datetime.now(tz=pytz.utc) + timedelta(hours=3)
        if record_user_achieve.current_repeats >= record_achieve.needed_repeats:
            record_user.rating += record_achieve.points

            record_user_achieve.is_got = True
            record_user_achieve.got_times += 1

            if record_achieve.day_count_reachieve is not None:
                record_user_achieve.reachieve_date = (now + timedelta(days=record_achieve.day_count_reachieve, seconds=0)).date()

            text = f"[id{record_user.id}|{record_user.firstname}] получил достижение " \
                   f"{record_achieve.name} и за это ему начисленно {record_achieve.points} очков."

            status = 2

            if achieve_id not in self.avoid_achieves:
                self.send_message(chat_id=event.chat_id,
                                  text=text)
            print(text)
            commit(db, record_user)

        commit(db, record_user_achieve)

        print(f"user {record_user.id} added one repeat in achieve id {record_achieve.id}\n"
              f"And now he has {record_user_achieve.current_repeats} repeats")

        return status

    def vote_achieve(self, event: VkBotMessageEvent, db: Session, option: bool):
        message: VkMessage = make_vk_message_schema(event.message)

        for_user = message.text
        for_user = int(re.search(r'[\d]{8,10}', for_user).group(0))

        record_user_achieve: UserAchieve = get_user_achieve_record(for_user, 7, event.chat_id, db)
        if record_user_achieve is None:
            record_user_achieve = self.make_empty_record_in_users_achieves(event=event, db=db, user_id=for_user, achieve_id=7)

        commit(db, record_user_achieve)

        moscow_zone = pytz.timezone("Europe/Moscow")
        now = datetime.now(tz=moscow_zone)
        if record_user_achieve.is_got and (record_user_achieve.reachieve_date is None or record_user_achieve.reachieve_date > now.date()):
            self.send_message(chat_id=event.chat_id,
                              text=f"Для [id{for_user}| него] больше нельзя запускать голосования сегодня.")
            return
        is_available = self.achieve_got(achieve_id=6, for_user=message.from_id, db=db, event=event)
        if is_available == 0:
            self.send_message(chat_id=event.chat_id,
                              text=f"Для [id{message.from_id}|тебя] больше недоступен запуск голосований сегодня.")
            return
        self.achieve_got(achieve_id=7, for_user=for_user, db=db, event=event)
        self.start_vote(db=db, event=event, option=option)

    def check_tag(self, event: VkBotMessageEvent, db: Session) -> None:
        message: VkMessage = make_vk_message_schema(event.message)
        record_group: Group = get_group_record(event.chat_id, db)
        if "id" + str(record_group.today_pdr) in message.text.lower():
            is_got = self.achieve_got(achieve_id=4, for_user=message.from_id, event=event, db=db)
            if is_got > 0:
                record_achieve: Achieves = get_achieve_record(achieve_id=4, db=db)
                record_achieve.is_available = False
                commit(db=db, inst=record_achieve)
                self.send_message(chat_id=event.chat_id,
                                  text="Это была секретная ачивка ;)\n"
                                       "Тебе нужно было тегнуть пидора дня в своём сообщении.")

    def my_achieves(self, event: VkBotMessageEvent, db: Session):
        message: VkMessage = make_vk_message_schema(event.message)
        user_achieves_list: List[UserAchieve] = db.query(UserAchieve).filter(UserAchieve.user_id == message.from_id).all()
        text = f"[id{message.from_id}|Вы] получали такие достижения:\n"
        for ach in user_achieves_list:
            if ach.achieve_id in self.avoid_achieves:
                continue
            if ach.got_times == 0:
                continue
            achieve: Achieves = get_achieve_record(achieve_id=ach.achieve_id, db=db)
            text += f"{achieve.name} {ach.got_times} раз \n"
        if text == f"[id{event.message['from_id']}|Вы] получали такие достижения:\n":
            self.send_message(chat_id=event.chat_id,
                              text="Вы ещё не получали никаких достижений.")
        else:
            self.send_message(chat_id=event.chat_id,
                              text=text)

    def fifteen_days(self, event: VkBotMessageEvent, db: Session) -> int:
        status = -1
        message: VkMessage = make_vk_message_schema(event.message)
        record_user_achieve: UserAchieve = get_user_achieve_record(message.from_id, 8, event.chat_id, db)

        if record_user_achieve is None:
            record_user_achieve = self.make_empty_record_in_users_achieves(event=event, db=db, user_id=message.from_id, achieve_id=8)

        moscow_zone = pytz.timezone("Europe/Moscow")
        now = datetime.now(tz=moscow_zone)
        if (record_user_achieve.last_date is None) or (now.date() - record_user_achieve.last_date.date()).days > 0:
            status = self.achieve_got(achieve_id=8, for_user=message.from_id, event=event, db=db)
        return status

    """def delete_last_msg(self, event: VkBotMessageEvent):
        msg_id = bot_last_message[event.chat_id]
        self.vk.messages.delete(cmids=msg_id, delete_for_all=1, peer_id=2000000000+event.chat_id)"""

    def listen(self):
        """Main func for listening events"""
        longpoll = VkBotLongPoll(self.vk_session, 209871225)

        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                if event.from_chat and event.message["from_id"] > 0:
                    session: Session = get_db()
                    message: VkMessage = make_vk_message_schema(event.message)
                    message_text: str = message.text
                    randoms = ['рандом', 'кто пидор?', 'рандомчик', 'пидор дня', 'заролить']
                    year = ['годовалый', 'пидор года']
                    pdr_stats = ['титулы', 'кол-во пидоров', 'статистика титулы', 'статистика']
                    fucked_stats = ['статистика пассивных']
                    ratings = ['рейтинги', 'таблица', 'лидерборд']
                    pictures = ['пикчу', 'фотку', 'дай фотку', 'рофл', 'ор', 'хуикчу']
                    gifs = ['гифку', 'гифка', 'хуифка']

                    if message_text.lower() in randoms:
                        record_group: Group = session.query(Group).filter(Group.id == event.chat_id).first()

                        # Is record exist
                        if record_group is None:  # Make record if not
                            record_group = self.make_empty_record_in_groups(event=event, db=session)

                        moscow_zone = pytz.timezone("Europe/Moscow")
                        # Check if we had already chosen pdr user today
                        today = datetime.now(tz=moscow_zone).date()
                        if today != record_group.pdr_date:
                            with open("./DataBases/DayPhrase.json", 'r') as f:
                                read: str = f.read()
                                json_dict: dict = loads(read)

                            if str(today) != json_dict['date']:
                                phrase = randoms[my_random(len(randoms))]
                                json_dict['date'] = str(today)
                                json_dict['phrase'] = phrase
                                with open("./DataBases/DayPhrase.json", 'w') as f:
                                    dump(json_dict, f)
                            if message_text.lower() == json_dict['phrase']:
                                self.send_message(event.chat_id,
                                                  text=f"[id{message.from_id}|Ты] сегодня счастливчик")
                                self.random_pdr(db=session, event=event)
                                self.achieve_got(achieve_id=2, for_user=message.from_id, event=event, db=session)
                            else:
                                self.send_message(event.chat_id,
                                                  text=f"[id{message.from_id}|Ты] не угадал сегодняшнюю фразу")
                        else:
                            self.random_pdr(db=session, event=event)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() in year:
                        self.pdr_of_the_year(db=session, event=event)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() in pdr_stats:
                        self.statistics(db=session, event=event, option=1)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() == "моя статистика":
                        self.personal_stats(event=event, db=session)
                        pers_stat_ach: Achieves = get_achieve_record(achieve_id=3, db=session)
                        if pers_stat_ach.is_available:
                            status = self.achieve_got(achieve_id=3, for_user=message.from_id, event=event, db=session)
                            if status == 2:
                                pers_stat_ach.is_available = False
                                commit(db=session, inst=pers_stat_ach)
                                self.send_message(chat_id=event.chat_id,
                                                  text="Это была секретная ачивка ;)\n "
                                                       "Идея тут в целом ни в чём просто, заюзать команду"
                                                       "'моя статистика' 2 раза за час")
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() in fucked_stats:
                        self.statistics(db=session, event=event, option=2)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() in ratings:
                        self.statistics(db=session, event=event, option=3)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif '@all' in message_text.lower():
                        suka_ach: Achieves = get_achieve_record(achieve_id=9, db=session)
                        self.suka_all(session, event)
                        if suka_ach.is_available:
                            status = self.achieve_got(achieve_id=9, for_user=message.from_id, event=event, db=session)
                            if status == 2:
                                suka_ach.is_available = False
                                commit(db=session, inst=suka_ach)
                                self.send_message(chat_id=event.chat_id,
                                                  text="Ты конечно пидорас, что так часто юзаешь all, но ты нашёл секретную ачивку")
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif "@online" in message_text.lower():
                        online_ach: Achieves = get_achieve_record(achieve_id=11, db=session)
                        if online_ach.is_available:
                            status = self.achieve_got(achieve_id=11, for_user=message.from_id, event=event, db=session)
                            if status == 2:
                                online_ach.is_available = False
                                commit(db=session, inst=online_ach)
                                self.send_message(chat_id=event.chat_id,
                                                  text="Чё, сука, хотел обойти систему? -- ну ладно обошёл, получай свою ачивку...")

                    elif message_text.lower() in pictures or re.fullmatch(r"о+р+", message_text.lower()):
                        self.send_picture(event=event)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif re.fullmatch(r'\+rep\s\[id[\d]{8,10}\|.*]', message_text.lower()):
                        self.vote_achieve(event=event, db=session, option=True)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif re.fullmatch(r'-rep\s\[id[\d]{8,10}\|.*]', message_text.lower()):
                        self.vote_achieve(event=event, db=session, option=False)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() == "отменить голосование" and message.from_id == 221767748:
                        self.hand_end_vote(db=session, event=event)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() == "голос за":
                        self.say_vote(db=session, event=event, option=True)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() == "голос против":
                        self.say_vote(db=session, event=event, option=False)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif message_text.lower() == "проверить голосование":
                        self.vote_check(db=session, event=event)
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                    elif re.search(r'\[id[\d]{8,10}\|.*]', message_text.lower()):
                        tag_ach: Achieves = get_achieve_record(achieve_id=4, db=session)
                        if tag_ach.is_available:
                            self.check_tag(event=event, db=session)
                    elif message_text.lower() in gifs:
                        self.send_gif(event=event)
                    elif message_text.lower() == "мои достижения":
                        self.my_achieves(event=event, db=session)
                    elif message_text.lower() == 'команды':
                        text = ""
                        text += f"Выбор пидора дня: {', '.join(randoms)};\n " \
                                f"Выбор пидора года: {', '.join(year)};\n" \
                                f"Показ статистики титулов: {', '.join(pdr_stats)};\n" \
                                f"Показ статистики пассивных: {', '.join(fucked_stats)};\n" \
                                f"Хочешь чтоб тебя послали нахуй? Попробуй написать all;\n" \
                                f"Чтобы узнать статистику только по тебе, используй 'моя статистика';\n" \
                                f"Показать рейтинги участников: {', '.join(ratings)};\n" \
                                f"Скинуть рандомную фотку из рофло альбома: {', '.join(pictures)};\n" \
                                f"Скинуть рандомную гифку: {', '.join(gifs)};\n" \
                                f"Запустить голосование на +- рейтинг: +rep или -rep, " \
                                f"а дальше нужно тегнуть человека через пробел, во время голосования, есть 3 команды:" \
                                f"'голос за', 'голос против' и 'проверить голосование';\n" \
                                f"Показать все ваши достижения: мои достижения."
                        print(f"Выполнил команду {message_text.lower()} от {message.from_id} в чате {event.chat_id}")
                        self.send_message(event.chat_id,
                                          text=text)
                    else:
                        ind = find_word(make_vk_message_schema(event.message))
                        if ind is not None:
                            self.send_gif(event=event, index=ind)
                            gif_send: Achieves = get_achieve_record(achieve_id=10, db=session)
                            if gif_send.is_available:
                                status = self.achieve_got(achieve_id=10, for_user=message.from_id, event=event, db=session)
                                if status == 2:
                                    gif_send.is_available = False
                                    commit(db=session, inst=gif_send)
                                    self.send_message(chat_id=event.chat_id,
                                                      text="Ты открыл новый функционал бота и "
                                                           "заработал секретную ачивку, красава.\n"
                                                           "Теперь вы можете с помощью определённых слов "
                                                           "вызывать соответсвующую гифку."
                                                           "Позови Лёху, он запостит полный список слов для гифок.")
                        elif chat_last_message[event.chat_id][::-1] == message_text.lower():
                            self.achieve_got(achieve_id=12, for_user=message.from_id, event=event, db=session)
                            self.send_message(chat_id=event.chat_id,
                                              text=f"Это была секретная ачивка, "
                                                   f"нужно было написать последнее сообщение наоборот ;)")
                        else:
                            fifteen_days_ach: Achieves = get_achieve_record(achieve_id=8, db=session)
                            if fifteen_days_ach.is_available:
                                status = self.fifteen_days(event=event, db=session)
                                if status == 2:
                                    fifteen_days_ach.is_available = False
                                    commit(db=session, inst=fifteen_days_ach)
                                    self.send_message(chat_id=event.chat_id,
                                                      text="Это была секретная ачивка ;)")
                    if len(message_text.lower()) >= 3:
                        chat_last_message[event.chat_id] = message_text.lower()
                    session.close()


if __name__ == '__main__':
    bot = Bot()
    print("Бот запущен")
    bot.listen()
