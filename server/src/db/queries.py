"""
SQL queries and table definitions for the user management database.

This module defines the database schema and SQL queries for:
- User account management
- File structure storage
- User authentication

Database Schema:
    users:
        user_id         - INTEGER PRIMARY KEY AUTOINCREMENT
        email          - TEXT UNIQUE NOT NULL
        password       - STRING(255) NOT NULL
        salt           - VARCHAR(255)
        files_directory - TEXT

    user_data:
        user_id        - INTEGER PRIMARY KEY (FK to users)
        files_structure - BLOB (Pickled data)

Query Categories:
    - Table Creation
    - User Management
    - File Structure Management
"""

# Table and column names
USERS_TABLE = 'users'
USER_DATA_TABLE = 'user_data'
USER_ID_ENTRY = 'user_id'
EMAIL_ENTRY = 'email'
PW_ENTRY = 'password'
SALT_ENTRY = 'salt'
FILES_DIR_ENTRY = 'files_directory'
FILES_STRUCT_ENTRY = 'files_structure'

# Table Creation Queries
CREATE_USERS_TABLE = f"""
CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
    {USER_ID_ENTRY} INTEGER PRIMARY KEY AUTOINCREMENT,
    {EMAIL_ENTRY} TEXT UNIQUE NOT NULL,
    {PW_ENTRY} STRING(255) NOT NULL,
    {SALT_ENTRY} VARCHAR(255), 
    {FILES_DIR_ENTRY} TEXT
);
"""

CREATE_USER_DATA_TABLE = f"""
CREATE TABLE IF NOT EXISTS {USER_DATA_TABLE} (
    {USER_ID_ENTRY} INTEGER PRIMARY KEY,
    {FILES_STRUCT_ENTRY} BLOB,  -- Pickled data
    FOREIGN KEY ({USER_ID_ENTRY}) REFERENCES {USERS_TABLE}({USER_ID_ENTRY})
);
"""

# User Management Queries
INSERT_USER = f"INSERT INTO {USERS_TABLE} ({EMAIL_ENTRY}, {PW_ENTRY}, {SALT_ENTRY}) VALUES (?, ?, ?);"

SELECT_USER_PW_SALT = f"SELECT {PW_ENTRY}, {SALT_ENTRY} FROM {USERS_TABLE} WHERE {EMAIL_ENTRY} = ?;"

FIND_USER = f"SELECT * FROM {USERS_TABLE} WHERE {EMAIL_ENTRY} = ?;"

SELECT_USER_ID = f"SELECT {USER_ID_ENTRY} FROM {USERS_TABLE} WHERE {EMAIL_ENTRY} = ?;"

SELECT_ALL_USERS = f"SELECT * FROM {USERS_TABLE};"

# File Structure Management Queries
SET_FILE_STRUCT = f"""
INSERT INTO {USER_DATA_TABLE} ({USER_ID_ENTRY}, {FILES_STRUCT_ENTRY})
VALUES (?, ?)
ON CONFLICT({USER_ID_ENTRY}) DO UPDATE SET
    {FILES_STRUCT_ENTRY} = excluded.{FILES_STRUCT_ENTRY};
"""

SELECT_FILE_STRUCT = f"""
SELECT ud.{FILES_STRUCT_ENTRY}
FROM {USERS_TABLE} u
JOIN {USER_DATA_TABLE} ud ON u.{USER_ID_ENTRY} = ud.{USER_ID_ENTRY}
WHERE u.{EMAIL_ENTRY} = ?;
"""