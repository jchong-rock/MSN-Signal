import json
from abc import ABC, abstractmethod
import hashlib
import random
import string
from readerwriterlock import rwlock
from list_numbers import ListNumbers
from auth.errors import *

class UserDatabase(ABC):
    DEFAULT_GROUP = "Other%20Contacts"
    def __init__(self):
        self.user_threads = {}
        self.switchboard = None
        self.user_threads_lock = rwlock.RWLockFairD()
    def set_connection_for_user(self, connection, username):
        with self.user_threads_lock.gen_wlock():
            self.user_threads[username] = connection
    def get_connection_for_user(self, username):
        with self.user_threads_lock.gen_rlock():
            if username in self.user_threads:
                return self.user_threads[username]
            return None
    def set_switchboard(self, switchboard):
        self.switchboard = switchboard
    def get_switchboard(self):
        return self.switchboard
    @abstractmethod
    def check_username(self, username):
        # should return True if database contains {username}, False otherwise
        pass
    @abstractmethod
    def add_user(self, username, credentials):
        # adds user to database; returns True if user did not exist, False otherwise
        # credentials may be of any type necessary
        pass
    @abstractmethod
    def remove_user(self, username):
        # removes user from database; returns True if user existed, False otherwise
        pass
    @abstractmethod
    def get_phone_number(self, username):
        # returns the phone number associated with a given username
        # returns None if no phone number is associated with a user
        pass
    @abstractmethod
    def set_phone_number(self, username, number):
        # sets the phone number for a given username
        pass
    @abstractmethod
    def get_usernames_by_phone_number(self, number):
        # gets usernames associated with a given phone number
        # n.b. phone numbers are not necessarily uniquely associated with a username
        pass
    @abstractmethod
    def new_group(self, username, groupname):
        # defines a new group called {groupname} for user {username}
        # returns index of new group if one is created, None otherwise (e.g. already exists)
        pass
    @abstractmethod
    def del_group(self, username, groupnum):
        # removes group {groupnum} for user {username}
        # returns True if group is removed, False otherwise (e.g. does not exist)
        # the group {DEFAULT_GROUP} must not be removed
        # all contacts from {groupnum} should be moved to {DEFAULT_GROUP}
        pass
    @abstractmethod
    def add_to_group(self, username, groupnum, contact):
        # adds {contact} to {groupnum} for user {username}
        # returns SUCCESS if contact is added, {errno} otherwise (e.g. group does not exist)
        # contact must already be in {DEFAULT_GROUP} if {groupnum} != 0
        pass
    @abstractmethod
    def remove_from_group(self, username, groupnum, contact):
        # removes {contact} from {groupnum} for user {username}
        # returns SUCCESS if contact is removed, {errno} otherwise (e.g. contact is not in group)
        pass
    @abstractmethod
    def get_group_names(self, username):
        # returns names of all groups for username in groupnum order
        pass
    @abstractmethod
    def get_contacts(self, username):
        # returns list of contacts for {username}
        pass
    @abstractmethod
    def add_contact_to_list(self, username, contact_name, list_num):
        # adds contact for {username} to {list} with default group settings
        pass
    @abstractmethod
    def remove_contact_from_list(self, username, contact_name, list_num):
        # removes contact for {username} from {list}
        pass
    @abstractmethod
    def get_contact_info(self, username, contact_name):
        # returns contact info for {contact_name}
        pass
    @abstractmethod
    def get_contacts_from_list(self, username, list_pos):
        # returns list of contacts for {username} in {list_pos}
        pass
    @abstractmethod
    def get_nickname(self, username):
        # returns nickname for username
        pass
    @abstractmethod
    def set_nickname(self, username, nickname):
        # sets nickname for username
        pass

    class Contact():
        def __init__(self, contact_dict, username, nickname):
            self.username = username
            self.nickname = nickname
            self.groups = None
            self.phone = None
            for x in ['groups', 'phone']:
                try:
                    setattr(self, x, contact_dict[x])
                except KeyError:
                    pass


class MD5UserDatabase(UserDatabase):
    @abstractmethod
    def get_salt(self, username):
        # returns the salt for a given username
        pass
    @abstractmethod
    def check_response(self, username, response):
        # returns True if the challenge response matches the username, False otherwise
        pass

class MD5JSON(MD5UserDatabase):
    def __init__(self, json_file):
        super().__init__()
        self.json_file = json_file
        self.lock = rwlock.RWLockFairD()
        # read json
        with open(json_file, 'r') as f:
            self.database = json.load(f)

    def __write_back__(self):
        with open(self.json_file, 'w') as f:
            json.dump(self.database, f)

    def __get_defaults__(self, name):
        return {
            "groups": [],
            "phone": None
        }

    def check_username(self, username):
        with self.lock.gen_rlock():
            return username in self.database
    
    def add_user(self, username, credentials, nickname=None):
        if nickname is None:
            nickname = username
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        key = hashlib.md5(f"{credentials}{salt}".encode('utf-8')).hexdigest()
        with self.lock.gen_rlock():
            if self.check_username(username):
                return False
            with self.lock.gen_wlock():
                self.database[username] = {
                    "nickname": nickname,
                    "salt": salt, 
                    "key": key,
                    "groups": [UserDatabase.DEFAULT_GROUP],
                    "lists": {
                        "FL": [ # forward list
                            # "name@server.com"
                        ],
                        "AL": [ # allow list

                        ],
                        "BL": [ # block list

                        ],
                        "RL": [ # reverse list
                        
                        ]
                    },
                    "contacts": {
                        # "name@server.com" : {
                        #     "groups": [0, 1, ...],
                        #     "phone": None
                        # }
                    }
                }
                self.__write_back__()
        return True
    
    def remove_user(self, username):
        with self.lock.gen_rlock():
            if self.check_username(username):
                with self.lock.gen_wlock():
                    self.database.pop(username)
                    self.__write_back__()
                return True
        return False
    
    def get_salt(self, username):
        with self.lock.gen_rlock():
            return self.database[username]['salt']

    def check_response(self, username, response):
        with self.lock.gen_rlock():
            return self.database[username]['key'].lower() == response.lower()

    def get_phone_number(self, username):
        with self.lock.gen_rlock():
            if 'phone' in self.database[username]:
                return self.database[username]['phone']
            return None

    def set_phone_number(self, username, number):
        with self.lock.gen_wlock():
            if number is None:
                self.database[username].pop('phone', None)
            else:
                self.database[username]['phone'] = number
            self.__write_back__()

    def get_group_names(self, username):
        with self.lock.gen_rlock():
            return self.database[username]['groups']

    def get_contacts(self, username):
        with self.lock.gen_rlock():
            return [self.get_contact_info(username, k) for k in self.database[username]['contacts']]

    def get_nickname(self, username):
        with self.lock.gen_rlock():
            return self.database[username]['nickname']
    
    def set_nickname(self, username, nickname):
        with self.lock.gen_wlock():
            self.database[username]['nickname'] = nickname
            self.__write_back__()

    def get_contact_info(self, username, contact_name):
        with self.lock.gen_rlock():
            return self.Contact(self.database[username]['contacts'][contact_name], contact_name, self.database[contact_name]['nickname']) 

    def get_contacts_from_list(self, username, list_pos):
        with self.lock.gen_rlock():
            return [self.get_contact_info(username, k) for k in self.database[username]["lists"][list_pos]]

    def new_group(self, username, groupname):
        with self.lock.gen_rlock():
            if groupname not in self.database[username]['groups']:
                with self.lock.gen_wlock():
                    self.database[username]['groups'].append([groupname])
                    self.__write_back__()
                return len(self.database[username]['groups']) - 1
            return None
    
    def add_contact_to_list(self, username, contact_name, list_num):
        with self.lock.gen_rlock():
            if contact_name in self.database:
                if contact_name in self.database[username]['lists'][list_num]:
                    return USER_ALREADY_IN_LIST
                if list_num == ListNumbers.ALLOW_LIST and contact_name in self.database[username]['lists'][ListNumbers.BLOCK_LIST]:
                    return USER_IN_ALLOW_AND_BLOCK
                if list_num == ListNumbers.BLOCK_LIST and contact_name in self.database[username]['lists'][ListNumbers.ALLOW_LIST]:
                    return USER_IN_ALLOW_AND_BLOCK
                with self.lock.gen_wlock():
                    if contact_name not in self.get_contacts(username):
                        self.database[username]['contacts'][contact_name] = self.__get_defaults__(contact_name)
                    self.database[username]['lists'][list_num].append(contact_name)
                    self.__write_back__()
                if list_num == ListNumbers.FORWARD_LIST:
                    self.add_contact_to_list(contact_name, username, ListNumbers.REVERSE_LIST)
                return SUCCESS
            #FIXME: refactor to remove hardcoded signal.com
            if contact_name.split('@')[1] == 'signal.com':
                self.add_user(contact_name, "")
                return self.add_contact_to_list(username, contact_name, list_num)
        return NONEXISTENT_EMAIL

    def remove_contact_from_list(self, username, contact_name, list_num):
        with self.lock.gen_rlock():
            if contact_name in self.database:
                if contact_name not in self.database[username]['lists'][list_num]:
                    return USER_NOT_IN_LIST
                with self.lock.gen_wlock():
                    self.database[username]['lists'][list_num].remove(contact_name)
                    self.__write_back__()
                if list_num == ListNumbers.FORWARD_LIST:
                    self.remove_contact_from_list(contact_name, username, ListNumbers.REVERSE_LIST)
                return SUCCESS
        return NONEXISTENT_EMAIL     

    def add_to_group(self, username, groupnum, contact):
        with self.lock.gen_rlock():
            if groupnum < len(self.database[username]['groups']):
                if contact in self.get_contacts(username):
                    with self.lock.gen_wlock():
                        self.database[username]['contacts'][contact]['groups'].append(groupnum)
                        self.__write_back__()
                    return True
        return False

    def del_group(self, username, groupnum):
        if groupnum == 0:
            return False
        with self.lock.gen_rlock():
            if groupnum < len(self.database[username]['groups']):
                with self.lock.gen_wlock():
                    self.database[username]['groups'].pop(groupnum)
                    self.__write_back__()
                return True
        return False

    def remove_from_group(self, username, groupnum, contact):
        with self.lock.gen_rlock():
            if groupnum < len(self.database[username]['groups']):
                if contact in self.get_contacts(username):
                    with self.lock.gen_wlock():
                        self.database[username]['contacts'][contact]['groups'].remove(groupnum)
                        self.__write_back__()
                    return True
        return False

    def get_usernames_by_phone_number(self, number):
        # O(n): do not use when possible
        # this is why an SQL implementation would be better
        users = []
        with self.lock.gen_rlock():
            for user in self.database:
                if user['phone'] == number:
                    users.append(user)
        return users
