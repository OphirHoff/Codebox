### Client --> Server ###
CODE_REGISTER = 'REGI'
CODE_LOGIN = 'LOGN'
CODE_RUN_SCRIPT = 'EXEC'
CODE_STORAGE_ADD = 'CREA'
CODE_GET_FILE = 'GETF'
CODE_SAVE_FILE = 'SAVF'
CODE_RUN_FILE = 'RUNF'

### Server --> Client ###
CODE_REGISTER_SUCCESS = 'REGR'
CODE_LOGIN_SUCCESS = 'LOGR'
CODE_OUTPUT = 'OUTP'
CODE_FILE_CONTENT = 'FILC'
CODE_FILE_SAVED = 'SAVR'
CODE_ERROR = 'ERRR'

### Error Codes ###
'''
001: General error
101: Login failed
102: User already exists (taken email address in registration)
201: File Was not found in the system
'''
ERROR_GENERAL = '001'
ERROR_LOGIN_FAILED = '101'
ERROR_USER_EXIST = '102'
ERROR_FILE_NOT_FOUND = '201'

class JsonEntries:

    # Create new file / directory
    NODE_TYPE = 'type'
    NODE_NAME = 'name'
    NODE_PATH = 'path'

    # Subdirectories
    SUB_DIRECTORY = 'children'
