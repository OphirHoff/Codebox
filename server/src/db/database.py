"""
SQLite database implementation for user management and file storage.

This module provides a thread-safe SQLite database interface for:
- User authentication (email/password)
- User file structure storage
- Secure password handling with salt

Database Schema:
    users:
        - id (INTEGER PRIMARY KEY)
        - email (TEXT UNIQUE)
        - password_hash (TEXT)
        - salt (BLOB)

    user_data:
        - user_id (INTEGER FK)
        - file_structure (BLOB)

Features:
    - Thread-safe database operations
    - Secure password hashing
    - Serialized file structure storage
    - User verification and authentication

Note:
    Database file is stored at 'data/users.sqlite'
"""

import sqlite3
import pickle
from utils import security, user_file_manager
import db.queries as queries
import datetime
import errors
import os
import threading

module_path = os.path.dirname(os.path.abspath(__file__))
DB_FILE = f"{module_path}/../../data/users.sqlite"

# Global lock for database access across all instances
db_lock = threading.Lock()


class Database:
    """
    Thread-safe SQLite database manager for user data.
    
    Handles:
    - Password hashing and verification
    - File structure storage and retrieval
    
    All database operations are protected by a global lock
    to ensure thread safety.
    """

    def __init__(self):
        """
        Initialize database connection and create tables if needed.
        Tables are defined in db.queries module.
        """
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()

        # Initialize db (will create tables only if needed)
        self.cursor.execute(queries.CREATE_USERS_TABLE)
        self.cursor.execute(queries.CREATE_USER_DATA_TABLE)

    def is_user_exist(self, email: str) -> bool:
        """
        Check if a user exists in the database.

        Args:
            email: User's email address

        Returns:
            bool: True if user exists, False otherwise
        """
        self.cursor.execute(queries.FIND_USER, (email,))
        user = self.cursor.fetchone()
        return bool(user)
    
    def get_user_id(self, email: str) -> int:
        """
        Get user's ID from their email address.

        Args:
            email: User's email address

        Returns:
            int: User's ID
        """
        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)

        self.cursor.execute(queries.SELECT_USER_ID, (email,))
        id: int = self.cursor.fetchone()[0]
        return id
    
    def is_password_ok(self, email: str, password: str) -> bool:
        """
        Verify user's password.

        Args:
            email: User's email address
            password: Password to verify

        Returns:
            bool: True if password matches, False otherwise
        """
        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)

        self.cursor.execute(queries.SELECT_USER_PW_SALT, (email,))
        res = self.cursor.fetchone()
        
        hashed_password, salt = res
        return hashed_password == security.hash_password(password, salt)
    
    def add_user(self, email: str, password: str, storage_struct: str = '[]', verf_code: str = None) -> bool:
        """
        Add a new user to the database.

        Args:
            email: User's email address
            password: User's password (will be hashed)
            storage_struct: Initial file structure (default: empty list)
            verf_code: Verification code (optional)

        Returns:
            bool: True if user was added, False if email already exists
        """
        if self.is_user_exist(email):
            return False

        hashed_pw, salt = security.generate_salt_hash(password)

        self.cursor.execute(queries.INSERT_USER, (email, hashed_pw, salt))
        self.conn.commit()

        return True

    def set_user_files_struct(self, email: str, storage_struct: user_file_manager.UserStorage) -> None:
        """
        Update user's file structure.

        Args:
            email: User's email address
            storage_struct: Updated file structure object
        """
        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)
        
        user_id = self.get_user_id(email)
        pickled_data = pickle.dumps(storage_struct)
        self.cursor.execute(queries.SET_FILE_STRUCT, (user_id, pickled_data))
        self.conn.commit()

    def get_user_files_struct(self, email: str) -> user_file_manager.UserStorage:
        """
        Retrieve user's file structure.

        Args:
            email: User's email address

        Returns:
            UserStorage: User's file structure object
        """
        if not self.is_user_exist(email):
            raise errors.UserNotFoundError(email)
        
        self.cursor.execute(queries.SELECT_FILE_STRUCT, (email,))
        pickled_data = self.cursor.fetchone()[0]
        return pickle.loads(pickled_data)

    def __str__(self) -> str:
        """Return string representation of all users in database."""
        self.cursor.execute(queries.SELECT_ALL_USERS)
        rows = self.cursor.fetchall()
        return str(rows)
