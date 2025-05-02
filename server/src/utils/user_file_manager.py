from pathlib import Path
from enum import Enum
import json
from db import database
import errors

USER_STORAGE_BASE_DIR = "../user_storage"
USER_FOLDER_NAME_PREFIX = "user_"
USER_ID_LEN = 3

class FileType(Enum):
    File = 'file'
    Folder = 'folder'


def _folder_name(uid: int):
    return f"{USER_STORAGE_BASE_DIR}/{USER_FOLDER_NAME_PREFIX}{str(uid).zfill(USER_ID_LEN)}"


class UserStorage():
    def __init__(self, user_id: int, files=[]):
        self.user_id = user_id
        self.files: list[dict] = files
        self.user_create_dir(self.user_id)

    def create_file(path: str, type: FileType, extension: str):
        pass

    def create_dir(path: str):
        pass

    def user_create_dir(self, uid: int):
    
        folder_path = Path(_folder_name(uid))

        if folder_path.exists():
            raise errors.UserStorageAlreadyExists()
        
        folder_path.mkdir()

    def __str__(self):
        return json.dumps(self.files)
