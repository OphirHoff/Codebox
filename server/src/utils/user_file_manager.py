from pathlib import Path
from enum import Enum
import json
from protocol import JsonEntries
import errors

USER_STORAGE_BASE_DIR = "../user_storage"
USER_FOLDER_NAME_PREFIX = "user_"
USER_ID_LEN = 3

class FileType(Enum):
    FILE = 'file'
    FOLDER = 'folder'


def user_folder_name(uid: int):
    return f"{USER_STORAGE_BASE_DIR}/{USER_FOLDER_NAME_PREFIX}{str(uid).zfill(USER_ID_LEN)}"

def get_file_content(uid: int, path: str):

    file_path = Path(f"{user_folder_name(uid)}/{path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {user_folder_name(uid)}/{path}")
    
    content = file_path.read_text(encoding="utf-8")
    return content

def update_file_content(uid: int, path: str, new_content: str):

    file_path = Path(f"{user_folder_name(uid)}/{path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {user_folder_name(uid)}/{path}")

    file_path.write_text(new_content, encoding="utf-8")


class UserStorage():
    def __init__(self, user_id: int, files=[]):
        self.user_id = user_id
        self.folder_name = user_folder_name(user_id)
        self.files: list[dict] = files
        self.create_user_storage()

    def create_file(self, path: str):

        file_path = Path(f"{self.folder_name}/{path}")

        if file_path.exists():
            raise errors.FileAlreadyExists(path)
        
        file_path.touch()
        self.update_tree(FileType.FILE, path)

    def delete_file(self, path: str):

        file_path = Path(f"{self.folder_name}/{path}")

        if not file_path.exists():
            raise FileNotFoundError()

        file_path.unlink()
        self.update_tree(None, path, remove=True)
        
    def create_dir(self, path: str):
        
        folder_path = Path(F"{self.folder_name}/{path}")

        if folder_path.exists():
            raise errors.FolderAlreadyExists(path)
        
        folder_path.mkdir()
        self.update_tree(FileType.FOLDER, path)

    def update_tree(self, node_type: FileType, path: str, remove=False):
        """ Update user files tree. """

        path: list = path.split('/')
        to_add = path.pop(-1)

        current = self.files  # Holds current directory node in the tree

        if path:  # Iterate only if not in the root dir of user's storage
            for i in range(len(path)):

                curr_node = path.pop(0)    
                found_next_node = False

                # Find the next node in path
                for node in current:
                    if node[JsonEntries.NODE_NAME] == curr_node and node[JsonEntries.NODE_TYPE] == FileType.FOLDER.value:
                        current = node[JsonEntries.SUB_DIRECTORY]
                        found_next_node = True
                
                # In case node was not found
                if not found_next_node:
                    raise FileNotFoundError(f"Path not found: {path}")

        if remove:
            for dir in current:
                if dir[JsonEntries.NODE_NAME] == to_add:
                    current.remove(dir)
                    break
                    

        else:
            # Create new node & add to tree
            if node_type == FileType.FILE:
                new_node = {
                    JsonEntries.NODE_TYPE: node_type.value,
                    JsonEntries.NODE_NAME: to_add
                    }
            
            else:
                new_node = {
                    JsonEntries.NODE_TYPE: node_type.value,
                    JsonEntries.NODE_NAME: to_add,
                    JsonEntries.SUB_DIRECTORY: []
                    }

            current.append(new_node)

    def find_node_in_tree(self, path: str):
        
        path: list = path.split('/')
        to_add = path.pop(-1)

        current = self.files  # Holds current directory node in the tree

        if path:  # Iterate only if not in the root dir of user's storage
            for i in range(len(path)):

                curr_node = path.pop(0)    
                found_next_node = False

                # Find the next node in path
                for node in current:
                    if node[JsonEntries.NODE_NAME] == curr_node and node[JsonEntries.NODE_TYPE] == FileType.FOLDER.value:
                        current = node[JsonEntries.SUB_DIRECTORY]
                        found_next_node = True
                
                # In case node was not found
                if not found_next_node:
                    raise FileNotFoundError(f"Path not found: {path}")
        
        return current

    def create_user_storage(self):
    
        folder_path = Path(self.folder_name)

        if folder_path.exists():
            raise errors.UserStorageAlreadyExists()
        
        folder_path.mkdir()

    def __str__(self):
        return json.dumps(self.files, indent=4)
