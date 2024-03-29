#!/usr/bin/python3
"""
Скрипт для автоматического тестирования email тестов 573.
Логирование команд происходит в консоли.
Работа с SMTP, POP3 и IMAP

Источник:
https://habr.com/ru/post/51772/
https://habr.com/ru/company/truevds/blog/262819/
https://www.dmosk.ru/instruktions.php?object=python-mail

SMTP https://code.tutsplus.com/ru/tutorials/sending-emails-in-python-with-smtp--cms-29975
     https://habr.com/ru/post/495256/

POP3 https://www.code-learner.com/python-use-pop3-to-read-email-example/

IMAP http://python-3.ru/page/imap-email-python
"""
import time
import os
import smtplib  # Импортируем библиотеку по работе с SMTP
from email import message_from_string
from email import encoders  # Импортируем энкодер
from email.mime.base import MIMEBase  # Общий тип файла
from email.mime.text import MIMEText  # Тип для Текста/HTML
from email.mime.multipart import MIMEMultipart  # Многокомпонентный объект
import poplib  # Библиотека для POP3
import imaplib  # Библиотека для IMAP
import base64  # Библиотека кодировки Base64
import csv  # Библиотека для работы с CSV файлами
from logger import get_time, log_csv, my_lan_ip, my_wan_ip  # Импорт логирования

I_FIRST = True  # True - инициатор, False - автоответчик
NEW_MILES = 0  # Маркер определения новых писем
STOP_READ_EMAIL = 0  # Маркер завершения функции
TIMEOUT = 30
__COUNT_SUBJECTS = True  # Маркер для логирования


def send_email(list_from: list, list_to: list, list_msg: list, list_cc=None, list_bcc=None):
    # Все данные в списках должны иметь строковый тип
    # list_from список отправителя, формат: [email , pass, почтовый сервера, порт почтового сервера]
    # list_to список получателя, формат: [email №1, ..., email №n]
    # list_msg список для формирования письма, формат: [тема письма, текст письма, относительный путь к файлу]
    # list_cc (необязательный аргумент) список адресов копии, формат: [email №1, ..., email №n]
    # list_bcc (необязательный аргумент) список адресов скрытой копии, формат: [email №1, ..., email №n]

    global I_FIRST

    if list_cc is None:
        list_cc = []
    if list_bcc is None:
        list_bcc = []

    # Формирование тела письма
    msg = MIMEMultipart(boundary="/")  # Создаем сообщение
    msg["From"] = list_from[0]  # Добавление отправителя
    msg["To"] = ", ".join(list_to)  # Добавление получателей
    msg["Cc"] = ", ".join(list_cc)  # Добавление копии
    msg["Bcc"] = ", ".join(list_bcc)  # Добавление скрытой копии
    msg["Subject"] = f"{list_msg[0]} {get_time() if len(list_msg) != 4 else ''}"  # Добавление темы сообщения
    msg.attach(MIMEText(list_msg[1], "plain"))  # Добавляем в сообщение текст

    if I_FIRST and len(list_msg) <= 3:
        # Логирование
        msg_TO = f"TO:{list_to}"
        msg_TO += f"  CC:{list_cc}" if len(list_cc) != 0 else ""
        msg_TO += f"  BCC:{list_bcc}" if len(list_bcc) != 0 else ""

        msg_TEXT = f"SUB:{list_msg[0]}  TEXT:{list_msg[1]}"
        msg_TEXT += f"  FILE:{list_msg[2]}" if len(list_msg) > 2 else ""

        # Запись лога в csv файл
        # protocol;time;resource;size;from;to;msg;error;
        log_csv(f"EMAIL-SMTP;{get_time()};;;{list_from[0]};{msg_TO};  {msg_TEXT}  ;;")

    # Условие для определения вложения у письма
    if len(list_msg) == 3:
        filepath = f"data/{list_msg[2]}"  # Путь к файлу. Файлы для отправки должны лежать в ./email/
        filename = f"{list_msg[2]}"  # Только имя файла

        with open(filepath, "rb") as fp:
            file = MIMEBase("application", "pdf")  # Используем общий MIME-тип
            file.set_payload(fp.read())  # Добавляем содержимое общего типа (полезную нагрузку)
            fp.close()

        encoders.encode_base64(file)  # Содержимое должно кодироваться как Base64
        file.add_header("Content-Disposition", "attachment", filename=filename)  # Добавляем заголовки
        msg.attach(file)  # Присоединяем файл к сообщению

    # Условие для отправки письма о выполненном тесте
    elif len(list_msg) == 4:
        # Добавляем к письму файл DOCX
        filepath_docx = f"./logs_in_docx/{list_msg[2]}"  # Путь к файлу
        filename_docx = f"{list_msg[2]}"  # Только имя файла
        with open(filepath_docx, "rb") as fp:
            file_docx = MIMEBase("application", "msword")  # Используем общий MIME-тип
            file_docx.set_payload(fp.read())  # Добавляем содержимое общего типа (полезную нагрузку)
            fp.close()
        encoders.encode_base64(file_docx)  # Содержимое должно кодироваться как Base64
        file_docx.add_header("Content-Disposition", "attachment", filename=filename_docx)  # Добавляем заголовки
        msg.attach(file_docx)  # Присоединяем файл к сообщению

        # Добавляем к письму файл CSV
        filepath_csv = f"./logs/{list_msg[3]}"  # Путь к файлу
        filename_csv = f"{list_msg[3]}"  # Только имя файла
        with open(filepath_csv, "rb") as fp:
            file_csv = MIMEBase("text", "csv")  # Используем общий MIME-тип
            file_csv.set_payload(fp.read())  # Добавляем содержимое общего типа (полезную нагрузку)
            fp.close()
        encoders.encode_base64(file_csv)  # Содержимое должно кодироваться как Base64
        file_csv.add_header("Content-Disposition", "attachment", filename=filename_csv)  # Добавляем заголовки
        msg.attach(file_csv)  # Присоединяем файл к сообщению

    server = smtplib.SMTP(list_from[2], int(list_from[3]))  # Создаем объект SMTP (сервер, порт)
    # server.set_debuglevel(1)  # Системные логи, дебагер
    server.starttls() if list_from[2] != "mail.nic.ru" else None  # Начинаем шифрованный обмен по TLS, нужен для яндекса
    server.login(list_from[0], list_from[1])  # Получаем доступ (email, пароль)
    server.send_message(msg)  # Отправляем сообщение

    # Убираем лог при отправке письма с тестовыми файлами
    if len(list_msg) == 4:
        server.quit()  # Выходим
        return

    # Логирование
    print(f"SEND  {get_time()}")
    print(f"FROM: {msg['From']}")
    print(f"  TO: {msg['To']}")
    print(f"  CC: {msg['Cc']}") if len(list_cc) != 0 else None
    print(f" BCC: {msg['Bcc']}") if len(list_bcc) != 0 else None
    print(f" SUB: {msg['Subject']}")
    print(f"TEXT: {list_msg[1]}")
    print(f"FILE: {list_msg[2]}") if len(list_msg) > 2 else None

    server.quit()  # Выходим
    return


def read_email(info_email: list, protocol: str):
    # info_email список el: str in [email, pass, server]
    # protocol либо "POP3", либо "IMAP"
    global I_FIRST, NEW_MILES, STOP_READ_EMAIL, __COUNT_SUBJECTS, TIMEOUT

    if protocol == "POP3":
        # Подключаемся к серверу, для Яндекса нужен SSL
        server = poplib.POP3(info_email[2]) if I_FIRST else poplib.POP3_SSL(info_email[2])
        # server.set_debuglevel(1)  # Системный лог, дебагер
        server.user(info_email[0])  # Email
        server.pass_(info_email[1])  # Пароль
        mails = int(server.stat()[0])  # Количество писем в ящике

    elif protocol == "IMAP":
        server = imaplib.IMAP4_SSL(info_email[2])
        server.debug = True
        server.login(info_email[0], info_email[1])
        # Выводит список папок в почтовом ящике.
        server.select("inbox")  # Подключаемся к папке "входящие"
        dir_inbox = server.search(None, "ALL")[1]  # Запрос о наполненности ящика
        id_list = dir_inbox[0].split()  # Получаем сроку номеров писем
        mails = int(id_list[-1]) if len(id_list) != 0 else 0  # Берем последний ID
    else:
        raise NameError(f"{get_time()} PROTOCOL ERROR: not found type protocol POP3 or IMAP to email_data.csv")

    max_mails_in_box = 10
    NEW_MILES = mails

    # Вечный цикл мониторинга новых писем
    while NEW_MILES == mails:
        STOP_READ_EMAIL += 1

        server.quit() if protocol == "POP3" else server.close()  # Закрываем соединение

        time.sleep(TIMEOUT * 2)

        # Условие для завершения функции
        if STOP_READ_EMAIL == 5 and I_FIRST:
            log_msg = f"*** NOT NEW MAILS {get_time()} ***"
            log_csv(f"ERROR EMAIL-{protocol};{get_time()};;;;;;{log_msg};") if __COUNT_SUBJECTS else None
            print(log_msg)
            STOP_READ_EMAIL = 0
            return

        if protocol == "POP3":
            # Подключаемся к серверу, для Яндекса нужен SSL
            server = poplib.POP3(info_email[2]) if I_FIRST else poplib.POP3_SSL(info_email[2])
            # server.set_debuglevel(1)  # Системный лог, дебагер
            server.user(info_email[0])  # Email
            server.pass_(info_email[1])  # Пароль
            NEW_MILES = int(server.stat()[0])
        elif protocol == "IMAP":
            server.select("inbox")  # Подключаемся к папке "входящие"
            dir_inbox = server.search(None, "ALL")[1]  # Запрос о наполненности ящика
            id_list = dir_inbox[0].split()  # Получаем сроку номеров писем
            NEW_MILES = int(id_list[-1]) if len(id_list) != 0 else 0  # Берем последний ID

        if NEW_MILES < mails:
            NEW_MILES = mails

    # Обработка сообщения
    if protocol == "POP3":
        lines = server.retr(NEW_MILES)[1]  # Получаем тело сообщения
        # b'\r\n'.join(lines) Подготавливаем сообщение к декодированию.
        # decode('utf-8') Декодируем сообщение по UTF-8 -> str
        # split("--/") создаём список на основе декодированного сообщения, элементы списка делятся по маркеру "--/"
        msg_content = b'\r\n'.join(lines).decode('utf-8').split("--/")

        # Защита от ошибок при получении письма не от функции send_email
        if len(msg_content) < 3:
            print("***** EMAIL: CONTROL ERROR - Not AUTO mail *****")
            return
    else:
        # для IMAP: *server.fetch(latest_email_id, "(RFC822)")[1][0]][1] Подготавливаем сообщение к декодированию
        # путём распаковки tuple decode('utf-8') Декодируем сообщение по UTF-8 -> str split("--/") создаём список на
        # основе декодированного сообщения, элементы списка делятся по маркеру "--/" Тело письма в необработанном
        # виде включает в себя заголовки и альтернативные полезные нагрузки
        msg_content = [*server.fetch(str(NEW_MILES), "(RFC822)")[1][0]][1].decode("utf-8").split("--/")  # Тело письма

        # Защита от ошибок при получении письма не от функции send_email
        if len(msg_content) < 3:
            print("***** EMAIL: CONTROL ERROR - Not AUTO mail *****")
            return

    msg_head = message_from_string(msg_content[0])  # Преобразуем str -> dict
    # Декодируем сообщение base64 -> UTF-8 -> str
    msg_text = base64.b64decode("".join(msg_content[1].split()[7:])).decode('utf-8')
    # Условие для определения вложенного файла и присвоение его имени
    msg_file = msg_content[2].split()[8][10:-1] if len(msg_content) > 3 else None

    msg_subject_decode = str()
    for el in (msg_head.get('Subject')).split():
        # Декодируем тему сообщения base64 -> UTF-8 -> str
        msg_subject_decode += base64.b64decode(el[10:-2]).decode('utf-8')

    if not I_FIRST and __COUNT_SUBJECTS:
        __COUNT_SUBJECTS = False
        print(f"\n\nEMAIL {get_time('date')}")
        print("--------------------------------------------------------------------------")

    print(f"READ  {get_time()} {protocol}")
    print(f"FROM: {msg_head.get('From')}")  # Вытаскиваем значение по ключу
    print(f"  TO: {msg_head.get('To')}")  # Вытаскиваем значение по ключу
    # Вытаскиваем значение по ключу если оно есть
    print(f"  CC: {msg_head.get('Cc')}") if msg_head.get('Cc') != (None or "") else None
    # Вытаскиваем значение по ключу если оно есть
    print(f" BCC: {msg_head.get('Bcc')}") if msg_head.get('Bcc') is not None else None
    print(f" SUB: {msg_subject_decode}")
    print(f"TEXT: {msg_text}")
    print(f"FILE: {msg_file}") if msg_file is not None else None  # Имя вложенного файла если оно есть

    if I_FIRST and __COUNT_SUBJECTS:
        # Логирование
        msg_TO = f"TO:{msg_head.get('To')}"
        msg_TO += f"  CC: {msg_head.get('Cc')}" if msg_head.get('Cc') != (None or "") else ""
        msg_TO += f" BCC: {msg_head.get('Bcc')}" if msg_head.get('Bcc') is not None else ""

        msg_TEXT = f"SUB:{msg_subject_decode}  TEXT:{msg_text}"
        msg_TEXT += f"  FILE:{msg_file}" if msg_file is not None else ""

        # Запись лога в csv файл
        # protocol;time;resource;size;from;to;msg;error;
        log_csv(f"EMAIL-{protocol};{get_time()};;;{msg_head.get('From')};{msg_TO};  {msg_TEXT}  ;;")

    # pop3 Удаление старых писем
    if mails > max_mails_in_box and protocol == "POP3":
        # print_in_log(":::::::::::::::::::::::::::::::::::::::::::::::::")
        for i in range(mails - max_mails_in_box):
            server.dele(i + 1)
            # print_in_log(f"Delete mail №{i + 1}")
        # print_in_log(":::::::::::::::::::::::::::::::::::::::::::::::::")

    # imap Удаление старых писем
    elif mails > max_mails_in_box and protocol == "IMAP":
        # print_in_log(":::::::::::::::::::::::::::::::::::::::::::::::::")
        for i in range(mails - max_mails_in_box):
            server.store(str(i + 1), '+FLAGS', '\\Deleted')
            # print_in_log(f"Delete mail №{i+1}")
        # print_in_log(":::::::::::::::::::::::::::::::::::::::::::::::::")

    server.quit() if protocol == "POP3" else server.close()  # Закрываем соединение
    STOP_READ_EMAIL = 0
    return


# Защита от отсутствия файла
try:
    # Для защиты данных используется файл email_data.csv, пример заполнения:
    #   var_sender, var_reader, email, password, server_smtp, port_smtp, server_imap/pop3
    #   sender_1,reader_1_pop3,test_1@ya.ru,pa$$word,smtp.ya.ru,587,pop3.yandex.ru
    #   sender_2,reader_2_imap,test_2@ya.ru,pa$$word,smtp.ya.ru,587,imap.yandex.ru

    # Открываем файл email_data.csv c данными для подключения:
    with open("config/email_data.csv", "r") as email_data:
        email_data_list = csv.reader(email_data)  # Преобразуем строку из файла в список
        email_data_dict = {}  # Словарь для записи данных
        for line in email_data_list:
            email_data_dict[line[0]] = line[2:-1]  # Отправитель
            email_data_dict[line[1]] = [line[2], line[3], line[-1]]  # Получатель
        email_data.close()
except FileNotFoundError:
    print("***** EMAIL: CONTROL ERROR - CSV File Not Found *****")  # Логирование.

# Отравитель №1
sender_1 = email_data_dict["sender_1"]

# Письмо №1
to_1 = ["rtc-nt-test1@yandex.ru", "rtc-nt-test2@yandex.ru", "rtc-nt-test3@yandex.ru"]
bcc_1 = ["rtc-nt-test4@yandex.ru"]
msg_1 = ["АВТО Отправка письма с 3 получателями, копией и вложением",  # Тема письма
         "Текст письма Отправка",  # Текст письма
         "constitution.pdf"]  # Прикреплённый файл из ./email/
# Письмо №3
to_3 = ["rtc-nt-test1@yandex.ru"]
cc_3 = ["rtc-nt-test2@yandex.ru", "rtc-nt-test3@yandex.ru"]
msg_3 = ["АВТО Отправка письма с 2 копиями и иероглифами",
         "لِيَتَقَدَّسِ اسْمُكَ"]  # Текст письма

# Отравитель №2
sender_2 = email_data_dict["sender_2"]

# Письмо №2
to_2 = ["test@rtc-nt.ru", "rtc-nt-test2@yandex.ru", "rtc-nt-test3@yandex.ru"]
msg_2 = ["АВТО Получение письма с 3 получателями и вложением",  # Тема письма
         "Текст письма Получение",  # Текст письма
         "constitution.pdf"]  # Прикреплённый файл из ./email/
# Письмо №4
to_4 = ["test@rtc-nt.ru"]
cc_4 = ["rtc-nt-test2@yandex.ru", "rtc-nt-test3@yandex.ru"]
msg_4 = ["АВТО Получение письма с 2 копиями и иероглифами",  # Тема письма
         "لِيَتَقَدَّسِ اسْمُكَ"]  # Текст письма

# Получатель №1 POP3
reader_1_pop3 = email_data_dict["reader_1_pop3"]
# Получатель №2 IMAP
reader_2_imap = email_data_dict["reader_2_imap"]


def i_sender():  # Отравитель
    print("\n\nEMAIL")
    print("----------------------------------------------------------------------------")
    send_email(sender_1, to_1, msg_1, list_cc=bcc_1)  # Отправка Письма №1
    time.sleep(TIMEOUT)
    print()

    read_email(reader_1_pop3, "POP3")  # Получение письма № 2
    time.sleep(TIMEOUT)
    print()

    send_email(sender_1, to_3, msg_3, list_cc=cc_3)  # Отправка Письма №3
    time.sleep(TIMEOUT)
    print()

    read_email(reader_1_pop3, "POP3")  # Получение письма № 4
    print("--------------------------------------------------------------------------")
    print("EMAIL end")


def i_answer():  # Автоответчик

    global I_FIRST, __COUNT_SUBJECTS

    print(f"\nАвтоответчик EMAIL запущен {get_time('date')} {get_time()}\n")

    while True:
        __COUNT_SUBJECTS = True
        I_FIRST = False

        read_email(reader_2_imap, "IMAP")  # Получение письма № 1
        time.sleep(TIMEOUT)
        print()

        send_email(sender_2, to_2, msg_2)  # Отправка Письма №2
        time.sleep(TIMEOUT)
        print()

        I_FIRST = True
        read_email(reader_2_imap, "IMAP")  # Получение письма № 3
        I_FIRST = False
        time.sleep(TIMEOUT)
        print()

        send_email(sender_2, to_4, msg_4, list_cc=cc_3)  # Отправка Письма №4
        print("--------------------------------------------------------------------------")
        print(f"EMAIL end {get_time('date')}")


def send_end_test(object_name, file_name_docx):
    # Функция отправки сообщения о выполненном тесте

    list_files = tuple(os.walk("logs"))[0][-1]  # Получаем список файлов внутри ./logs
    list_files.sort()

    file_name_csv = list_files[-1]
    msg_for_check = f"На проверку \n{get_time('for_pu')}\n{my_lan_ip()}\n{my_wan_ip()}"

    to_me = ["ns@rtc-nt.ru"]
    msg_end_test = [f"АВТО Тесты ПД 573 {object_name}", msg_for_check, file_name_docx, file_name_csv]

    send_email(sender_1, to_me, msg_end_test)
