from pathlib import Path
from db import database
import errors

USER_STORAGE_BASE_DIR = "../user_storage"
USER_FOLDER_NAME_PREFIX = "user_"
USER_ID_LEN = 3

def _folder_name(uid: int):
    return f"{USER_STORAGE_BASE_DIR}/{USER_FOLDER_NAME_PREFIX}{str(uid).zfill(USER_ID_LEN)}"

def user_create_dir(uid: int):
    
    folder_path = Path(_folder_name(uid))

    if folder_path.exists():
        raise errors.UserStorageAlreadyExists()
    
    folder_path.mkdir()