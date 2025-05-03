class CustomError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class InvalidRequestCodeError(CustomError):
    def __init__(self, message="Received invalid request code from client."):
        super().__init__(message)

class UserNotFoundError(CustomError):
    def __init__(self, email):
        super().__init__(f"No user found with email '{email}'")

class UserStorageAlreadyExists(CustomError):
    def __init__(self, message="Tried to create storage folder that already exists."):
        super().__init__(message)

class FileAlreadyExists(CustomError):
    def __init__(self, path):
        super().__init__(f"Tried to create file ({path}) which already exists.")

class FolderAlreadyExists(CustomError):
    def __init__(self, path):
        super().__init__(f"Tried to create folder ({path}) which already exists.")

class InvalidEntry(CustomError):
    def __init__(self, entry, value):
        super().__init__(f"Invalid Json/dictionary entry encountered - {entry}: {value}")