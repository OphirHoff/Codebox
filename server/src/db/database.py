import sqlite3
import pickle
import os
from utils import security, user_file_manager
import db.queries as queries
import datetime
import errors

DB_FILE = "../data/users.sqlite"

# indexes
PW = 0
SALT = 1
CODE = 2

class Database:
    def __init__(self):

        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()

        # Initialize db (will create tables only if needed)
        self.cursor.execute(queries.CREATE_USERS_TABLE)
        self.cursor.execute(queries.CREATE_USER_DATA_TABLE)

    def is_user_exist(self, email):

        self.cursor.execute(queries.FIND_USER, (email,))
        user = self.cursor.fetchone()
        return bool(user)
    
    def get_user_id(self, email):
        
        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)

        self.cursor.execute(queries.SELECT_USER_ID, (email,))
        id: int = self.cursor.fetchone()[0]
        return id
    
    def is_password_ok(self, email, password):

        # salt = self.cursor.execute(queries.SELECT_USER_SALT, (email,))
        # hashed_password = self.cursor.execute(queries.SELECT_USER_PW, (email,))

        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)

        self.cursor.execute(queries.SELECT_USER_PW_SALT, (email,))
        res = self.cursor.fetchone()
        
        hashed_password, salt = res

        return hashed_password == security.hash_password(password, salt)

    # def is_code_ok(self, email, code):
    #     if self.data[email][CODE] != '':
    #         print(self.data[email][CODE][0] == code)
    #         return self.data[email][CODE][0] == code
    #     return False

    # def get_code(self, email):
    #     if self.data[email][CODE] != '':
    #         return self.data[email][CODE][0]
    #     return False
    
    def add_user(self, email, password, storage_struct='[]', verf_code=None):
        ''' Returns true if successful, False is user already exists. '''
        if self.is_user_exist(email):
            return False

        hashed_pw, salt = security.generate_salt_hash(password)

        self.cursor.execute(queries.INSERT_USER, (email, hashed_pw, salt))
        self.conn.commit()

        return True

        # self.data[email] = hashed_pw

        # exp_time = datetime.datetime.now() + datetime.timedelta(minutes=code_expiry)
        # self.data[email].append((verf_code, exp_time))


    def set_user_files_struct(self, email, storage_struct: user_file_manager.UserStorage):

        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)
        
        user_id = self.get_user_id(email)
        pickled_data = pickle.dumps(storage_struct)
        self.cursor.execute(queries.SET_FILE_STRUCT, (user_id, pickled_data))
        self.conn.commit()

    def get_user_files_struct(self, email) -> user_file_manager.UserStorage:

        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)
        
        self.cursor.execute(queries.SELECT_FILE_STRUCT, (email,))
        pickled_data = self.cursor.fetchone()[0]
        return pickle.loads(pickled_data)

    # ↓  ↓  ↓  ↓  to fix  ↓  ↓  ↓  ↓
    def reset_password(self, email, new_password):
        hashed_pw, salt = security.generate_salt_hash(new_password)
        self.data[email][PW] = hashed_pw
        self.data[email][SALT] = salt

    def update_securitycode(self, email, code):
        exp_time = datetime.datetime.now() + datetime.timedelta(minutes=code_expiry)
        self.data[email][CODE] = (code, exp_time)

    def delete_user(self, email):
            del self.data[email]

    def is_code_expired(self, email):
        if self.data[email][CODE] != '':
            return self.data[email][CODE][1] < datetime.datetime.now()
        return False

    def waiting_for_verify(self, email):
        if self.data[email][CODE] != '':
            return self.data[email][CODE][1] > datetime.datetime.now()

    def reset_code_expiry(self, email):
        self.data[email][CODE] = ''

    def update(self):
        with open(DB_FILE, 'wb') as file:
            pickle.dump(self.data, file)

    def __str__(self):
        self.cursor.execute(queries.SELECT_ALL_USERS)
        rows = self.cursor.fetchall()
        return str(rows)
