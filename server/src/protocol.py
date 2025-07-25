"""
Protocol definition for client-server communication.

This module defines the message codes used in the communication protocol between
the client and server components. It includes:

Client to Server codes:
    - Authentication: Registration and login
    - File operations: Create, read, save, delete, download
    - Execution: Run scripts and handle input

Server to Client codes:
    - Operation responses and confirmations
    - Error notifications with specific error codes

Error codes are three-digit numbers categorized by their first digit:
    - 0xx: General errors
    - 1xx: Authentication errors
    - 2xx: Execution errors
    - 3xx: File operation errors
"""

### Client --> Server ###
CODE_REGISTER = 'REGI'
CODE_LOGIN = 'LOGN'
CODE_RUN_SCRIPT = 'EXEC'
CODE_STORAGE_ADD = 'CREA'
CODE_GET_FILE = 'GETF'
CODE_SAVE_FILE = 'SAVF'
CODE_RUN_FILE = 'RUNF'
CODE_INPUT = 'INPR'
CODE_DELETE_FILE = 'DELF'
CODE_DOWNLOAD_FILE = 'DNLD'
CODE_LOGOUT = 'OUTT'

### Server --> Client ###
CODE_REGISTER_SUCCESS = 'REGR'
CODE_LOGIN_SUCCESS = 'LOGR'
CODE_OUTPUT = 'OUTP'
CODE_BLOCKED_INPUT = 'INPT'
CODE_RUN_END = 'DONE'
CODE_STORAGE_UPDATED = 'CRER'
CODE_FILE_CONTENT = 'FILC'
CODE_FILE_SAVED = 'SAVR'
CODE_FILE_DELETED = 'DELR'
CODE_FILE_TO_DOWNLOAD = 'DNLR'
CODE_ERROR = 'ERRR'

### Error Codes ###
'''
001: General error
101: Login failed
102: User already exists (taken email address in registration)
201: File Was not found in the system
202: Execution Failed
203: Execution exeeded max run time
301: Failed to create file or folder
302: Failed to delete file
'''
ERROR_GENERAL = '001'
ERROR_LOGIN_FAILED = '101'
ERROR_USER_EXIST = '102'
ERROR_FILE_NOT_FOUND = '201'
ERROR_EXECUTION_TIMEOUT = '202'
ERROR_STORAGE_CREATE = '301'
ERROR_FILE_DELETE = '302'

class JsonEntries:
    """Defines JSON field names used in file and directory operations."""

    # Create new file / directory
    NODE_TYPE = 'type'
    NODE_NAME = 'name'
    NODE_PATH = 'path'

    # Subdirectories
    SUB_DIRECTORY = 'children'
