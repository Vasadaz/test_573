#!/usr/bin/python3
"""
Скрипт для автоматического тестирования im тестов 573.
Логирование команд происходит в консоли.
Работа с протоколом XMPP

Источник:
https://slixmpp.readthedocs.io/en/latest/index.html
https://slixmpp.readthedocs.io/en/latest/api/clientxmpp.html
https://stackru.com/questions/4521237/kak-otklyuchit-shifrovanie-v-lokalnoj-seti-xmpp
"""
import asyncio
import csv
import time

from slixmpp import ClientXMPP

from logger import get_time, log_csv  # Импорт логирования

try:
    # Только для Windows. Для работы скрипта на Windows, иначе ошибка NotImplementedError
    # Источник: https://github.com/saghul/aiodns/issues/78
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except AttributeError:
    pass

READ_WAIT_MSG = "Прочитанное сообщение"  # Для записи содержимого из прочитанного сообщений, используется для условий
ANSWER_WAIT_MSG = "Текст, который должен входить в READ_WAIT_MSG"  # Для записи ожидаемого ответа
TIMEOUT = 10


class SendMsgBot(ClientXMPP):
    # Класс для отправки сообщения, аргументы:
    # jid аккаунт jabber и его пароль password
    # recipient получатель сообщения
    # message текст сообщения

    def __init__(self, jid: str, password: str, recipient: str, message: str):
        ClientXMPP.__init__(self, jid, password)  # Создание клиента для подключения
        self.connect(disable_starttls=True)  # Подключение к серверу без шифрования disable_starttls
        self.recipient, self.msg = recipient, message  # Перенаправление аргументов в среду self
        self.add_event_handler("session_start", self.session_start)  # Метод запуска сессии

    def session_start(self, event):
        self.send_presence()  # Должно работать, хз зачем, но иначе никак
        self.get_roster()  # Должно работать, хз зачем, но иначе никак
        self.sender_msg()  # Запуск функции sender_msgz

    def sender_msg(self):
        self.msg = f"{self.msg} {get_time()}"
        self.send_message(mto=self.recipient, mbody=self.msg, mtype='chat')  # Отправка сообщения

        # Логирование
        print(f"SEND  {get_time()}")
        print(f"FROM: {self.jid}")
        print(f"  TO: {self.recipient}")
        print(f" MSG: {self.msg}")

        self.disconnect()  # Отключение от сервера

        # Запись лога в csv файл
        # protocol;time;resource;size;from;to;msg;error;
        log_csv(f"IM-send;{get_time()};;;{self.jid};{self.recipient};{self.msg};;")


class ReadMsgBot(ClientXMPP):
    # Класс для чтения сообщения, аргументы:
    # jid аккаунт jabber и его пароль password

    def __init__(self, jid: str, password: str, i_answer_obj=False):
        ClientXMPP.__init__(self, jid, password)  # Создание клиента для подключения
        self.connect(disable_starttls=True)  # Подключение к серверу без шифрования disable_starttls
        self.jid, self.i_answer_obj = jid, i_answer_obj  # Переопределяем аргументы в локальные переменные
        self.add_event_handler("session_start", self.session_start)  # Метод запуска сессии
        self.add_event_handler("message", self.message)  # Метод для обработки сообщений

    def session_start(self, event):
        self.send_presence()  # Должно работать, хз зачем, но иначе никак
        self.get_roster()  # Должно работать, хз зачем, но иначе никак

    def message(self, msg):
        global ANSWER_WAIT_MSG, READ_WAIT_MSG

        if self.i_answer_obj:  # Условие логирование для режима answer
            print(f"\n\nIM {get_time('date')}")
            print("----------------------------------------------------------------------------")

        msg_list = str(msg).split('"')  # Преобразование сообщения в список для логирования
        msg_list_from = msg_list[1].split('/')[0]  # Определение отправителя
        msg_list_to = msg_list[3]  # Определение получателя

        for el in msg_list:
            if "<body>" in el:
                READ_WAIT_MSG = el.split("body")[1][1:-2]  # Определение текста в сообщении

        if ANSWER_WAIT_MSG in READ_WAIT_MSG:
            # Логирование
            print(f"READ  {get_time()}")
            print(f"FROM: {msg_list_from}")
            print(f"  TO: {msg_list_to}")
            print(f" MSG: {READ_WAIT_MSG}")

            self.disconnect()

            # Запись лога в csv файл
            # protocol;time;resource;size;from;to;msg;error;
            log_csv(f"IM-read;{get_time()};;;{msg_list_from};{msg_list_to};{READ_WAIT_MSG};;")


def tasks_killer():
    # Принудительное закрытие сопрограмм для избежания предупреждений со стороны asyncio.
    loop = asyncio.get_event_loop()
    tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]

    for task in tasks:
        asyncio.Task.cancel(task)


def fun_sender(jid: str, password: str, recipient: str, message: str):
    # Функция для отправки сообщения
    # jid аккаунт jabber и его пароль password
    # recipient получатель сообщения
    # message текст сообщения
    sender = SendMsgBot(jid, password, recipient, message)
    # Запуск процесса с отключением при первом же событии (forever=False) - здесь это отправка сообщения
    sender.process(forever=False)

    tasks_killer()


def fun_reader(jid: str, password: str, waiting_msg: str, i_answer_fun=False):
    # Функция для чтения сообщения
    # jid аккаунт jabber и его пароль password
    # waiting_msg какое сообщение мы должны прочитать, т.е. на что потом отвечать
    # i_answer_fun для определения будет находиться в режиме ожидания сообщения
    global ANSWER_WAIT_MSG, READ_WAIT_MSG, TIMEOUT

    ANSWER_WAIT_MSG = waiting_msg

    reader = ReadMsgBot(jid, password, i_answer_fun)

    if i_answer_fun:
        while ANSWER_WAIT_MSG not in READ_WAIT_MSG:
            # Цикл работает до тех пор, пока не будет получено сообщение с текстом = waiting_msg
            # Запуск процесса с отключением при первом же событии (forever=False) - здесь это чтение сообщения
            reader.process(forever=False)
    else:
        # Запуск процесса на 120 секунд м последующим отключением
        reader.process(timeout=(TIMEOUT * 2))

    tasks_killer()


# Защит от отсутствия файла
try:
    # Для защиты данных используется файл im_data.csv, пример заполнения:
    #   var_name;jid;password
    #   jid_1;test_1@ya.ru;pa$$word
    #   jid_2;test_1@ya.ru;pa$$word

    # Открываем файл im_data.csv c данными для подключения
    with open("config/im_data.csv", "r") as im_data:
        im_data_list = csv.reader(im_data)  # Преобразуем строку из файла в список
        im_data_dict = {}  # Словарь для записи данных
        for line in im_data_list:
            im_data_dict[line[0]] = line[1:]  # Имя переменной:аккаунт
        im_data.close()
except FileNotFoundError:
    print("***** IM: CONTROL ERROR - CSV File Not Found *****")  # Логирование.

# sender и его сообщения
jid_1 = im_data_dict["jid_1"]
jid_1_msg_1 = "test out"
jid_1_msg_2 = "Отправка сообщения"

# answer и его сообщения
jid_2 = im_data_dict["jid_2"]
jid_2_msg_1 = "test in"
jid_2_msg_2 = "Получение сообщения"


def i_sender():
    # Сценарная функция для инициализатора переписки, т.е. он отправляет сообщение первым, а потом ждёт входящего
    print("\n\nIM")
    print("----------------------------------------------------------------------------")
    fun_sender(jid_1[0], jid_1[1], jid_2[0], jid_1_msg_1)
    print()
    time.sleep(TIMEOUT)

    fun_reader(jid_1[0], jid_1[1], jid_2_msg_1)
    print()
    time.sleep(TIMEOUT)

    fun_sender(jid_1[0], jid_1[1], jid_2[0], jid_1_msg_2)
    print()
    time.sleep(TIMEOUT)

    fun_reader(jid_1[0], jid_1[1], jid_2_msg_2)
    print("----------------------------------------------------------------------------")
    print("IM end")

    tasks_killer()


def i_answer():
    print(f"\nАвтоответчик IM запущен {get_time('date')} {get_time()}\n")

    while True:
        fun_reader(jid_2[0], jid_2[1], jid_1_msg_1, i_answer_fun=True)
        time.sleep(TIMEOUT)
        print()

        fun_sender(jid_2[0], jid_2[1], jid_1[0], jid_2_msg_1)
        time.sleep(TIMEOUT)
        print()

        fun_reader(jid_2[0], jid_2[1], jid_1_msg_2)
        time.sleep(TIMEOUT)
        print()

        fun_sender(jid_2[0], jid_2[1], jid_1[0], jid_2_msg_2)
        print("----------------------------------------------------------------------------")
        print(f"IM end {get_time('date')}")

        tasks_killer()
