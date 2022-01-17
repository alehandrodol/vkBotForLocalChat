import sys
from datetime import datetime

import vk_api
import os
from time import sleep

import pytz

from sqlalchemy.orm import Session
from vk_api.utils import get_random_id

from models import Group, User
from service_funcs import get_group_record, get_user_record, commit
from core.database import get_db


def auto_end_vote(db: Session, group_id: int, params: dict, vk) -> None:
    """This func ends voting"""
    record_group: Group = get_group_record(group_id, db)

    if record_group.active_vote == 0:
        return

    moscow_zone = pytz.timezone("Europe/Moscow")
    now = datetime.now(tz=moscow_zone)
    is_time = (now - record_group.start_time.astimezone(moscow_zone)).seconds > 50  # 3600 is 1 hour by secs
    if record_group.votes_counter >= 7 or (is_time and record_group.votes_counter > 0):
        winner_record: User = get_user_record(record_group.for_user_vote, record_group.id, db)
        winner_record.rating += (50 if record_group.active_vote == 1 else -50)
        vk.messages.send(
            key=(params['key']),
            server=(params['server']),
            ts=(params['ts']),
            random_id=get_random_id(),
            message=f"Голосование завершено "
                    f"{'по времени' if record_group.votes_counter < 7 else 'так как большенство, очевидно, ЗА'}.\n"
                    f"[id{winner_record.id}|{winner_record.firstname}] "
                    f"{'получил' if record_group.active_vote == 1 else 'потерял'} "
                    f"50 рейтинга.",
            chat_id=group_id
        )

        commit(db, winner_record)
    elif record_group.votes_counter <= -7 or (is_time and record_group.votes_counter <= 0):

        vk.messages.send(
            key=(params['key']),
            server=(params['server']),
            ts=(params['ts']),
            random_id=get_random_id(),
            message=f"Голосование завершенно "
                    f"{'по времени, результат отрицательный' if record_group.votes_counter < 7 else 'так как большенство, очевидно, ПРОТИВ'}.",
            chat_id=group_id
        )
    record_group.active_vote = 0
    commit(db, record_group)


def wait():
    db: Session = get_db()
    group_id = 1
    vk_session = vk_api.VkApi(
        token=os.environ.get("GROUP_TOKEN"))
    vk = vk_session.get_api()
    params = vk.groups.getLongPollServer(group_id=209871225)
    moscow_zone = pytz.timezone("Europe/Moscow")
    record_group: Group = get_group_record(group_id, db)
    db.close()
    while True:
        now = datetime.now(tz=moscow_zone)
        is_time = (now - record_group.start_time.astimezone(moscow_zone)).seconds > 50
        if is_time:
            db: Session = get_db()
            auto_end_vote(db=db, group_id=group_id, params=params, vk=vk)
            db.close()
            break


if __name__ == "__main__":
    wait()
