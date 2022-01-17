import vk_api
import os

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, VkBotMessageEvent


def listen():
    vk_session = vk_api.VkApi(
        token=os.environ.get("GROUP_TOKEN"))
    vk = vk_session.get_api()
    params = vk.groups.getLongPollServer(group_id=209871225)

    longpoll = VkBotLongPoll(vk_session, 209871225)

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if event.message['text'].lower() == "тест":
                print("найс")
            if event.message['text'].lower() == "стоп":
                break


if __name__ == "__main__":
    listen()
