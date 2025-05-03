from pathlib import Path
from enum import Enum
import json
import errors

USER_STORAGE_BASE_DIR = "../user_storage"
USER_FOLDER_NAME_PREFIX = "user_"
USER_ID_LEN = 3

class FileType(Enum):
    FILE = 'file'
    FOLDER = 'folder'


def user_folder_name(uid: int):
    return f"{USER_STORAGE_BASE_DIR}/{USER_FOLDER_NAME_PREFIX}{str(uid).zfill(USER_ID_LEN)}"


class UserStorage():
    def __init__(self, user_id: int, files=[]):
        self.user_id = user_id
        self.folder_name = user_folder_name(user_id)
        self.files: list[dict] = files
        self.user_create_dir()

    def create_file(self, path: str):

        file_path = Path(f"{self.folder_name}/{path}")

        if file_path.exists():
            raise errors.FileAlreadyExists(path)
        
        file_path.touch()
        
    def create_dir(self, path: str):
        
        folder_path = Path(F"{self.folder_name}/{path}")

        if folder_path.exists():
            raise errors.FolderAlreadyExists(path)
        
        folder_path.mkdir()

    def user_create_dir(self):
    
        folder_path = Path(self.folder_name)

        if folder_path.exists():
            raise errors.UserStorageAlreadyExists()
        
        folder_path.mkdir()

    def __str__(self):
        return json.dumps(self.files)
