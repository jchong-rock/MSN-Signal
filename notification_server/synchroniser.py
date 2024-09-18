from msn_patcher import MSNPatcher
from list_numbers import ListNumbers
from abc import abstractmethod
from auth.errors import *
from config import Configuration

class Synchroniser(MSNPatcher):
    @abstractmethod
    def return_syn(self, data):
        pass
    @abstractmethod
    def transfer(self, data):
        pass
    @abstractmethod
    def add_contact(self, data):
        pass
    @abstractmethod
    def remove_contact(self, data):
        pass
    @abstractmethod
    def change_status(self, data):
        pass

class SynchroniserMSNP6(Synchroniser):
    def __init__(self, database, connection):
        super().__init__(connection)
        self.database = database
        self.list_ver = 0
        self.func_table = {
            "SYN": self.return_syn,
            "CHG": self.change_status,
            "ADD": self.add_contact,
            "REM": self.remove_contact,
            "XFR": self.transfer,
            'change-status': self.relay_status_update
        }

    def return_syn(self, data):
        # for now we will always pretend we have more up to date contact info since it makes synchronisation easier
        trid = data[0]
        self.list_ver = int(data[1])+1
        self.connection.send(f"SYN {trid} {self.list_ver}")
        self.send_privacy_settings(trid)
        self.send_phone_info(trid)
        self.send_contacts(trid)

    def transfer(self, data):
        trid = data[0]
        dest = data[1]
        match dest:
            case "SB":
                self.transfer_to_switchboard(trid)
            # can be extended if there are other possible transfers
    
    def transfer_to_switchboard(self, trid):
        sb_ip, sb_port = self.database.get_switchboard()
        # use same auth string for everyone for now
        self.connection.send(f"XFR {trid} SB {sb_ip}:{sb_port} CKI {Configuration.sb_auth_string}")

    def send_privacy_settings(self, trid):
        # for now everyone gets the same privacy settings
        self.connection.send(f"GTC {trid} {self.list_ver} A")
        self.connection.send(f"BLP {trid} {self.list_ver} AL")

    def send_phone_info(self, trid):
        username = self.connection.username
        phone_number = self.database.get_phone_number(username)
        if phone_number is not None:
            num = phone_number.split()
            self.connection.send(f"PRP {trid} {self.list_ver} PHM {num[0]}%20{num[1]}")

    def send_contacts(self, trid):
        lists = {}
        for t in ListNumbers():
            lists[t] = self.database.get_contacts_from_list(self.connection.username, t)
            size = len(lists[t])
            if size == 0:
                self.connection.send(f"LST {trid} {t} {self.list_ver} 0 0")
            else:
                for ix, c in enumerate(lists[t]):
                    self.connection.send(f"LST {trid} {t} {self.list_ver} {ix+1} {size} {c.username} {c.nickname}")

    def change_status(self, data):
        trid = data[0]
        status = data[1]
        for k in self.database.get_contacts_from_list(self.connection.username, ListNumbers.FORWARD_LIST):
            cn = self.database.get_connection_for_user(k)
            if cn is not None:
                cn.tell(f'change-status {self.connection.username} {status}')
        self.connection.status = status
        self.connection.send(f"CHG {trid} {status}")
        self.get_statuses(trid)

    def get_statuses(self, trid):
        for k in self.database.get_contacts_from_list(self.connection.username, ListNumbers.FORWARD_LIST):
            cn = self.database.get_connection_for_user(k)
            if k.username.split("@")[1] == "signal.com": #FIXME: remove hardcoded signal.com
                self.connection.send(f"ILN {trid} NLN {k.username} {k.nickname}")
            elif cn is not None:
                self.connection.send(f"ILN {trid} {cn.status} {k.username} {k.nickname}")

    def relay_status_update(self, data):
        contact_name = data[0]
        status = data[1]
        if status == "FLN":
            self.connection.send(f"FLN {contact_name}")
        else:
            self.connection.send(f"NLN {status} {contact_name} {self.database.get_nickname(contact_name)}")
    
    def add_contact(self, data):
        trid = data[0]
        list_num = data[1]
        username = data[2]
        nickname = data[3]

        if not '@' in username:
            self.connection.error(MALFORMED_EMAIL, trid)
            return
        result = self.database.add_contact_to_list(self.connection.username, username, list_num)
        if result == SUCCESS:
            self.list_ver += 1
            self.connection.send(f"ADD {trid} {list_num} {self.list_ver} {username} {nickname}")
        else:
            self.connection.error(result, trid)

    def remove_contact(self, data):
        trid = data[0]
        list_num = data[1]
        username = data[2]

        if not '@' in username:
            self.connection.error(MALFORMED_EMAIL, trid)
            return
        result = self.database.remove_contact_from_list(self.connection.username, username, list_num)
        if result == SUCCESS:
            self.list_ver += 1
            self.connection.send(f"REM {trid} {list_num} {self.list_ver} {username}")
        else:
            self.connection.error(result, trid)


class SynchroniserMSNP7(SynchroniserMSNP6):
    #TODO
    def send_groups(self, trid, list_ver):
        group_names = self.database.get_group_names(self.connection.username)
        group_strings = []
        for ix, g in enumerate(group_names):
            group_strings.append(f"LSG {trid} {list_ver} {ix+1} {len(group_names)} {ix} {g} 0")
        self.connection.send_multi_line(group_strings)

class SynchroniserFactory():
    def __init__(self, database):
        self.database = database
    def __call__(self, connection):
        return SynchroniserMSNP6(self.database, connection)