import os
import vk_api

from json import dumps, loads

from datetime import datetime

from sqlalchemy.orm import Session

from models import Group, User, Achieves, UserAchieve, GroupAchieve
from schemas import VkUser, VkMessage

from pydantic import ValidationError
from typing import Union, Optional

from gifs_words import key_words


def auth_handler():
    key = input()
    remember_device = True
    return key, remember_device


def commit(db: Session, inst: Union[Group, User, Achieves, UserAchieve, GroupAchieve]):
    """Method for pushing records into DB"""
    print("Загружаю в базу вот такую строчку:", str(inst))
    db.add(inst)
    db.commit()
    db.refresh(inst)


def my_random(right_border: int) -> int:
    return datetime.today().microsecond % right_border


def get_group_record(group_id: int, db: Session) -> Group:
    record_group: Group = db.query(Group).filter(Group.id == group_id).first()
    return record_group


def get_user_record(user_id: int, group_id: int, db: Session) -> User:
    record_user: User = db.query(User).filter(User.id == user_id, User.chat_id == group_id).first()
    return record_user


def get_achieve_record(achieve_id: int, db: Session) -> Achieves:
    record_achieve: Achieves = db.query(Achieves).filter(Achieves.id == achieve_id).first()
    return record_achieve


def get_user_achieve_record(user_id: int, achieve_id: int, chat_id: int, db: Session) -> UserAchieve:
    record_user_achieve: UserAchieve = db.query(UserAchieve).filter(UserAchieve.user_id == user_id,
                                                                    UserAchieve.achieve_id == achieve_id,
                                                                    UserAchieve.chat_id == chat_id).first()
    return record_user_achieve


def get_group_achieve_record(group_id: int, achieve_id: int, db: Session) -> GroupAchieve:
    record_group_achieve: UserAchieve = db.query(UserAchieve).filter(GroupAchieve.group_id == group_id,
                                                                     GroupAchieve.achieve_id == achieve_id).first()
    return record_group_achieve


def make_vk_user_schema(user: dict) -> VkUser:
    user = dumps(user)
    try:
        user = VkUser.parse_raw(user)
    except ValidationError as e:
        print(e.json())
        raise e
    return user


def make_vk_message_schema(message: dict) -> VkMessage:
    message = dumps(message)
    try:
        message = VkMessage.parse_raw(message)
    except ValidationError as e:
        print(e.json())
        raise e
    return message


def user_api():
    login = os.environ.get("USER_LOGIN")
    password = os.environ.get("USER_PASS")
    vk_user_session = vk_api.VkApi(login, password, auth_handler=auth_handler)
    try:
        vk_user_session.auth()
    except vk_api.AuthError as e:
        print(e)
        return
    user_vk = vk_user_session.get_api()
    return user_vk


def find_word(message: VkMessage) -> Optional[int]:
    for word in key_words.keys():
        if word in message.text.lower():
            return key_words[word]
    return None


def add_new_column_in_json(ind: int):
    res = ""
    with open("DataBases/users_data.json", "r") as f:
        read = f.read()
        data_list: list[list] = loads(read)['values']
        new_list = []
        for ind1, record in enumerate(data_list):
            temp = record
            temp.insert(ind, temp[4]*100 + temp[5]*50)
            new_list.insert(ind1, temp)
        res_dict = {'values': new_list}
        res = dumps(res_dict, ensure_ascii=False)

    with open("DataBases/users_data.json", "w") as f:
        f.write(res)


if __name__ == "__main__":
    pass
