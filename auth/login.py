from config import Configuration
import parse
from msn_patcher import MSNPatcher
import sys
from auth.errors import *
from notification_server.synchroniser import SynchroniserFactory
import threading

class Login(MSNPatcher):
    def protocol_check(self, data):
        pass
    def version_check(self, data):
        trid = data[0]
        permitted_versions = Configuration.permitted_versions
        self.connection.send(f"VER {trid} {permitted_versions}")

class MD5Login(Login):
    def __init__(self, database, connection):
        super().__init__(connection)
        self.database = database
        self.func_table = {
            "INF": self.protocol_check,
            "USR": self.md5_auth,
            "VER": self.version_check
        }
        
    def protocol_check(self, data):
        trid = data.pop(0)
        self.connection.send(f"INF {trid} MD5")
    
    def md5_auth(self, data):
        trid = data[0]
        login_type = data[1]
        if login_type != "MD5":
            sys.stderr.write(f"Non-MD5 login attempted from {self.connection.client_address}")
            return
        key = data[3]
        match data[2]:
            case 'I':
                self.send_md5_salt(key, trid)
            case 'S':
                self.check_md5_response(key, trid)
            case _:
                sys.stderr.write(f"Malformed login from {self.connection.client_address}")
                return
        
    def check_md5_response(self, key, trid):
        if self.database.check_response(self.connection.username, key):
            self.connection.send(f"USR {trid} OK {self.connection.username} {self.connection.username}")
            self.database.set_connection_for_user(self.connection, self.connection.username)
            self.connection.add_patcher(SynchroniserFactory(self.database))
        else:
            self.connection.error(INVALID_CREDENTIALS, trid)

    def send_md5_salt(self, username, trid):
        self.connection.username = username
        if self.database.check_username(username):
            salt = self.database.get_salt(username)
            self.connection.send(f"USR {trid} MD5 S {salt}")
        else:
            self.connection.error(INVALID_CREDENTIALS, trid)

class MD5LoginFactory():
    def __init__(self, database):
        self.database = database
    def __call__(self, connection):
        return MD5Login(self.database, connection)
