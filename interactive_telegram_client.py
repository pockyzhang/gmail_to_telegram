import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')

import smtplib
import time
import imaplib
import email
from email.message import Message
import pprint
from bs4 import BeautifulSoup
import chardet
import sqlite3

import asyncio
import os
import sys
import time
from getpass import getpass

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.network import ConnectionTcpAbridged
from telethon.utils import get_display_name

# Create a global variable to hold the loop we will be using
loop = asyncio.get_event_loop()


#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@改这里三个@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#这个脚本写下来，最大的遗憾是 我还是不会处理exception
FROM_EMAIL  = "zbzb"+"@gmail.com"   #邮箱名字
FROM_PWD    = "zbzb"                #邮箱密码
channelName = 't.me/xxxxxx'         #频道invite link

#电报的信息
SESSION = 'MakeBigMoney'
API_ID = ''
API_HASH = ''
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


SMTP_SERVER = "imap.gmail.com"
SMTP_PORT   = 993
conn = sqlite3.connect("./MBM.db")
cursor = conn.cursor()

def read_email_from_gmail():
    try:
        mail = imaplib.IMAP4_SSL(SMTP_SERVER)
        mail.login(FROM_EMAIL,FROM_PWD)
        mail.select('INBOX')

        t, data = mail.search(None, 'ALL')
        mail_ids = data[0]
        print(mail_ids)

        id_list = mail_ids.split()   
        first_email_id = int(id_list[0])
        latest_email_id = int(id_list[-1])
        print(id_list)
        print(first_email_id)
        print(latest_email_id)

        if latest_email_id == 1 :
            first_email_id = 0

        for i in range(latest_email_id,first_email_id, -1):
            typ,data = mail.fetch(str(i).encode(),'(RFC822)')
            msg = email.message_from_string(data[0][1].decode('utf-8'))
            #这里的count是为了下面的for，第一个结果貌似是纯文字的，不是我要的，第二个才是html版本的
            count = 0
            msgId = msg.get("Message-ID")
            if fetchSig(msgId) == False:
                return ""
            #这里添加开始
            #用get()获取标题并进行初步的解码。
            #subject在测试中会出现两种情况
            sub = msg.get('Subject')
            subdecode = email.header.decode_header(sub)
            if subdecode[0][1] == None:
                title = subdecode[0][0]
            else :
                title = subdecode[0][0].decode(subdecode[0][1])
            #这里添加结束
            for part in msg.walk():
                if not part.is_multipart():
                    if count == 0:
                        count = 1
                        continue

                    c=str(part.get_payload(decode=True).decode("utf-8"))
                    #这里修改开始
                    # now = int(time.time())     # 
                    # timeArray = time.localtime(now)
                    # otherStyleTime = time.strftime("%Y-%m-%d-%H-%M-%S", timeArray)

                    #需求是 去掉一些页面内容
                    soup = BeautifulSoup(c,features="html.parser")
                    tb = soup.find('table',class_="m_-2077724439543498532post-meta")
                    if tb != None:
                        tb.clear()
                    # print(tb.clear())

                    btn = soup.find('table',class_='m_-2077724439543498532post-meta m_-2077724439543498532big')
                    if btn != None:
                        btn.clear()

                    foot = soup.find('div',class_='m_-2077724439543498532footer')
                    if foot != None:
                        foot.clear()

                    with open(title+".html",mode="w+",encoding="utf-16") as f:
                        f.write(soup.prettify())
                    return title+".html"
                    #这里修改结束     
    except Exception as e:
        print("??"+str(e))


def createDB():
    sql = '''create table if not exists gmail(sig text)'''
    cursor.execute(sql)
def fetchSig(theSig):
    sql = '''select * from gmail where sig=\"%s\"''' %(theSig)
    print(sql)
    result = cursor.execute(sql)
    if len(result.fetchall()) == 0:
        sql = '''insert into gmail(sig)values(\"%s\")'''%(theSig)
        print(sql)
        cursor.execute(sql)
        conn.commit()
        print('not exists')
        return True
    else:
        print('exists')
        return False


def sprint(string, *args, **kwargs):
    """Safe Print (handle UnicodeEncodeErrors on some terminals)"""
    try:
        print(string, *args, **kwargs)
    except UnicodeEncodeError:
        string = string.encode('utf-8', errors='ignore')\
                       .decode('ascii', errors='ignore')
        print(string, *args, **kwargs)


def print_title(title):
    """Helper function to print titles to the console more nicely"""
    sprint('\n')
    sprint('=={}=='.format('=' * len(title)))
    sprint('= {} ='.format(title))
    sprint('=={}=='.format('=' * len(title)))


def bytes_to_string(byte_count):
    """Converts a byte count to a string (in KB, MB...)"""
    suffix_index = 0
    while byte_count >= 1024:
        byte_count /= 1024
        suffix_index += 1

    return '{:.2f}{}'.format(
        byte_count, [' bytes', 'KB', 'MB', 'GB', 'TB'][suffix_index]
    )


async def async_input(prompt):
    """
    Python's ``input()`` is blocking, which means the event loop we set
    above can't be running while we're blocking there. This method will
    let the loop run while we wait for input.
    """
    print(prompt, end='', flush=True)
    return (await loop.run_in_executor(None, sys.stdin.readline)).rstrip()


def get_env(name, message, cast=str):
    """Helper to get environment variables interactively"""
    if name in os.environ:
        return os.environ[name]
    while True:
        value = input(message)
        try:
            return cast(value)
        except ValueError as e:
            print(e, file=sys.stderr)
            time.sleep(1)


class InteractiveTelegramClient(TelegramClient):
    """Full featured Telegram client, meant to be used on an interactive
       session to see what Telethon is capable off -

       This client allows the user to perform some basic interaction with
       Telegram through Telethon, such as listing dialogs (open chats),
       talking to people, downloading media, and receiving updates.
    """

    def __init__(self, session_user_id, api_id, api_hash,
                 proxy=None):
        """
        Initializes the InteractiveTelegramClient.
        :param session_user_id: Name of the *.session file.
        :param api_id: Telegram's api_id acquired through my.telegram.org.
        :param api_hash: Telegram's api_hash.
        :param proxy: Optional proxy tuple/dictionary.
        """
        print_title('Initialization')

        print('Initializing interactive example...')

        # The first step is to initialize the TelegramClient, as we are
        # subclassing it, we need to call super().__init__(). On a more
        # normal case you would want 'client = TelegramClient(...)'
        super().__init__(
            # These parameters should be passed always, session name and API
            session_user_id, api_id, api_hash,

            # You can optionally change the connection mode by passing a
            # type or an instance of it. This changes how the sent packets
            # look (low-level concept you normally shouldn't worry about).
            # Default is ConnectionTcpFull, smallest is ConnectionTcpAbridged.
            connection=ConnectionTcpAbridged,

            # If you're using a proxy, set it here.
            proxy=proxy
        )

        # Store {message.id: message} map here so that we can download
        # media known the message ID, for every message having media.
        self.found_media = {}

        # Calling .connect() may raise a connection error False, so you need
        # to except those before continuing. Otherwise you may want to retry
        # as done here.
        print('Connecting to Telegram servers...')
        try:
            loop.run_until_complete(self.connect())
        except ConnectionError:
            print('Initial connection failed. Retrying...')
            loop.run_until_complete(self.connect())

        # If the user hasn't called .sign_in() or .sign_up() yet, they won't
        # be authorized. The first thing you must do is authorize. Calling
        # .sign_in() should only be done once as the information is saved on
        # the *.session file so you don't need to enter the code every time.
        if not loop.run_until_complete(self.is_user_authorized()):
            print('First run. Sending code request...')
            user_phone = input('Enter your phone: ')
            loop.run_until_complete(self.sign_in(user_phone))

            self_user = None
            while self_user is None:
                code = input('Enter the code you just received: ')
                try:
                    self_user =\
                        loop.run_until_complete(self.sign_in(code=code))

                # Two-step verification may be enabled, and .sign_in will
                # raise this error. If that's the case ask for the password.
                # Note that getpass() may not work on PyCharm due to a bug,
                # if that's the case simply change it for input().
                except SessionPasswordNeededError:
                    pw = getpass('Two step verification is enabled. '
                                 'Please enter your password: ')

                    self_user =\
                        loop.run_until_complete(self.sign_in(password=pw))

    async def run(self):
        """Main loop of the TelegramClient, will wait for user action"""

        # Once everything is ready, we can add an event handler.
        #
        # Events are an abstraction over Telegram's "Updates" and
        # are much easier to use.
        self.add_event_handler(self.message_handler, events.NewMessage)
        createDB()
        # Enter a while loop to chat as long as the user wants
        while True:
            filePath = read_email_from_gmail()
            print(filePath)
            if filePath != '' and filePath != None:
                myEntity = await self.get_entity(channelName)
                # await self.send_message(myEntity, 'fck that', link_preview=False)
                await self.send_document(path=filePath, entity=myEntity)
            time.sleep(5*60)

    async def send_photo(self, path, entity):
        """Sends the file located at path to the desired entity as a photo"""
        await self.send_file(
            entity, path,
            progress_callback=self.upload_progress_callback
        )
        print('Photo sent!')

    async def send_document(self, path, entity):
        """Sends the file located at path to the desired entity as a document"""
        await self.send_file(
            entity, path,
            force_document=True,
            progress_callback=self.upload_progress_callback
        )
        print('Document sent!')

    async def download_media_by_id(self, media_id):
        """Given a message ID, finds the media this message contained and
           downloads it.
        """
        try:
            msg = self.found_media[int(media_id)]
        except (ValueError, KeyError):
            # ValueError when parsing, KeyError when accessing dictionary
            print('Invalid media ID given or message not found!')
            return

        print('Downloading media to usermedia/...')
        os.makedirs('usermedia', exist_ok=True)
        output = await self.download_media(
            msg.media,
            file='usermedia/',
            progress_callback=self.download_progress_callback
        )
        print('Media downloaded to {}!'.format(output))

    @staticmethod
    def download_progress_callback(downloaded_bytes, total_bytes):
        InteractiveTelegramClient.print_progress(
            'Downloaded', downloaded_bytes, total_bytes
        )

    @staticmethod
    def upload_progress_callback(uploaded_bytes, total_bytes):
        InteractiveTelegramClient.print_progress(
            'Uploaded', uploaded_bytes, total_bytes
        )

    @staticmethod
    def print_progress(progress_type, downloaded_bytes, total_bytes):
        print('{} {} out of {} ({:.2%})'.format(
            progress_type, bytes_to_string(downloaded_bytes),
            bytes_to_string(total_bytes), downloaded_bytes / total_bytes)
        )

    async def message_handler(self, event):
        """Callback method for received events.NewMessage"""

        # Note that message_handler is called when a Telegram update occurs
        # and an event is created. Telegram may not always send information
        # about the ``.sender`` or the ``.chat``, so if you *really* want it
        # you should use ``get_chat()`` and ``get_sender()`` while working
        # with events. Since they are methods, you know they may make an API
        # call, which can be expensive.
        chat = await event.get_chat()
        if event.is_group:
            if event.out:
                sprint('>> sent "{}" to chat {}'.format(
                    event.text, get_display_name(chat)
                ))
            else:
                sprint('<< {} @ {} sent "{}"'.format(
                    get_display_name(await event.get_sender()),
                    get_display_name(chat),
                    event.text
                ))
        else:
            if event.out:
                sprint('>> "{}" to user {}'.format(
                    event.text, get_display_name(chat)
                ))
            else:
                sprint('<< {} sent "{}"'.format(
                    get_display_name(chat), event.text
                ))


if __name__ == '__main__':
    # SESSION = os.environ.get('TG_SESSION', 'interactive')
    # API_ID = get_env('TG_API_ID', 'Enter your API ID: ', int)
    # API_HASH = get_env('TG_API_HASH', 'Enter your API hash: ')

    client = InteractiveTelegramClient(SESSION, API_ID, API_HASH)
    loop.run_until_complete(client.run())
