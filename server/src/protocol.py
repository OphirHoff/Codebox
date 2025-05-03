### Client --> Server ###
CODE_REGISTER = 'REGI'
CODE_LOGIN = 'LOGN'
CODE_RUN_SCRIPT = 'EXEC'
CODE_STORAGE_ADD = 'CREA'

### Server --> Client ###
CODE_REGISTER_SUCCESS = 'REGR'
CODE_LOGIN_SUCCESS = 'LOGR'
CODE_OUTPUT = 'OUTP'
CODE_ERROR = 'ERRR'

### Error Codes ###
'''
001: General error
101: Login failed
102: User already exists (taken email address in registration)

'''
ERROR_GENERAL = '001'
ERROR_LOGIN_FAILED = '101'
ERROR_USER_EXIST = '102'