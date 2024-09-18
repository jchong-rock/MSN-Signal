from msn_patcher import MSNPatcher
from auth.errors import *
from config import Configuration
from random import randint
from switchboard.signal import Signal

class SwitchBoard(MSNPatcher):

    def __init__(self, database, connection):
        super().__init__(connection)
        self.database = database
        self.contacts = []
        self.signals = {}
        self.sb_id = randint(100, 99999999)
        self.func_table = {
            "USR": self.authenticate,
            "CAL": self.call_user,
            "MSG": self.handle_message
        }

    def authenticate(self, data):
        trid = data[0]
        username = data[1]
        auth_token = data[2]
        if self.database.check_username(username) and auth_token == Configuration.sb_auth_string:
            nickname = self.database.get_nickname(username)
            self.connection.send(f"USR {trid} OK {username} {nickname}")
        else:
            self.connection.send(f"{INVALID_CREDENTIALS} {trid}")

    def call_user(self, data):
        trid = data[0]
        contact = data[1]
        k = self.database.get_connection_for_user(contact)
        self.contacts.append(contact)
        if contact.split('@')[1] == "signal.com": #FIXME: remove hardcoded signal.com
            self.connection.send(f"CAL {trid} RINGING {self.sb_id}")
            nickname = self.database.get_nickname(contact)
            self.signals[contact.split('@')[0]] = Signal(contact.split('@')[0], self)
            self.signals[contact.split('@')[0]].start()
            self.connection.send(f"JOI {contact} {nickname}")
        elif k is not None:
            addr = self.connection.get_address()
            nickname = self.database.get_nickname(self.connection.username)
            k.send(f"RNG {self.sb_id} {addr[0]}:{addr[1]} CKI {Configuration.sb_auth_string} {self.connection.username} {nickname}")
            self.connection.send(f"CAL {trid} RINGING {self.sb_id}")
        else:
            self.connection.send(f"{USER_OFFLINE} {trid}")

    def handle_message(self, data):
        #FIXME: remove magic numbers and magic strings
        trid = data[0]
        length = data[2]
        print("data: ", data)
        if data[6] == 'text/x-msmsgscontrol':
            return
        ix = data.index("PF=0") + 1
        msg = ''.join(f"{x} " for x in data[ix:])
        for c in self.contacts:
            if c.split('@')[1] == "signal.com":
                self.signals[c.split('@')[0]].send(msg)
            #TODO: implement for MSN
        self.connection.send(f"ACK {trid}")
                
    def send(self, msg, from_number):
        #FIXME: remove magic numbers and magic strings
        uname = f"{from_number}@signal.com"
        nickname = self.database.get_nickname(uname)
        length = 114 + len(msg)
        self.connection.send(f"MSG {uname} {nickname} {length}\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nX-MMS-IM-Format: FN=Arial; EF=I; CO=0; CS=0; PF=22\r\n\r\n{msg}")

    def __del__(self):
        for k in self.signals:
            k.join()

class SwitchBoardFactory():
    def __init__(self, database):
        self.database = database
    def __call__(self, connection):
        return SwitchBoard(self.database, connection)