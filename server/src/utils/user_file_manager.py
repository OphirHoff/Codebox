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
    """
    Generates the folder path for a user's storage directory.
    
    Creates a standardized folder name using the user ID with zero-padding
    to ensure consistent directory naming across the storage system.
    
    Args:
        uid: User ID to generate folder name for
        
    Returns:
        Formatted folder path string
    """
    return f"{USER_STORAGE_BASE_DIR}/{USER_FOLDER_NAME_PREFIX}{str(uid).zfill(USER_ID_LEN)}"

def get_file_content(uid: int, path: str):
    """
    Retrieves the content of a file from user's storage directory.
    
    Reads and returns the complete text content of the specified file
    using UTF-8 encoding. Validates file existence before reading.
    
    Args:
        uid: User ID to locate the storage directory
        path: Relative path to the file within user's storage
        
    Returns:
        File content as string
    """
    file_path = Path(f"{user_folder_name(uid)}/{path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {user_folder_name(uid)}/{path}")
    
    content = file_path.read_text(encoding="utf-8")
    return content

def update_file_content(uid: int, path: str, new_content: str):
    """
    Updates the content of an existing file in user's storage.
    
    Args:
        uid: User ID to locate the storage directory
        path: Relative path to the file within user's storage
        new_content: New content to write to the file
    """
    file_path = Path(f"{user_folder_name(uid)}/{path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {user_folder_name(uid)}/{path}")

    file_path.write_text(new_content, encoding="utf-8")


class UserStorage():
    """
    Manages file storage operations for a specific user.
    
    Handles creation, deletion, and organization of files and directories
    within a user's dedicated storage space.
    """
    def __init__(self, user_id: int, files=[]):
        """
        Initializes user storage manager.
        
        Args:
            user_id: Unique identifier for the user
            files: Optional list of existing files in the storage
        """
        self.user_id = user_id
        self.folder_name = user_folder_name(user_id)
        self.files: list[dict] = files
        self.create_user_storage()

    def create_file(self, path: str):
        """
        Creates a new empty file at the specified path.
        
        Args:
            path: Relative path where the file should be created
        """
        file_path = Path(f"{self.folder_name}/{path}")

        if file_path.exists():
            raise errors.FileAlreadyExists(path)
        
        file_path.touch()
        self.update_tree(FileType.FILE, path)

    def delete_file(self, path: str):
        """
        Deletes an existing file at the specified path.
        
        Args:
            path: Relative path to the file to delete
        """
        file_path = Path(f"{self.folder_name}/{path}")

        if not file_path.exists():
            raise FileNotFoundError()

        file_path.unlink()
        self.update_tree(None, path, remove=True)
        
    def create_dir(self, path: str):
        """
        Creates a new directory at the specified path.
        
        Args:
            path: Relative path where the directory should be created
        """
        folder_path = Path(F"{self.folder_name}/{path}")

        if folder_path.exists():
            raise errors.FolderAlreadyExists(path)
        
        folder_path.mkdir()
        self.update_tree(FileType.FOLDER, path)

    def update_tree(self, node_type: FileType, path: str, remove=False):
        """
        Updates the file tree structure after file operations.
        
        Args:
            node_type: Type of node (file or folder) to update
            path: Path to the node in the tree
            remove: Whether to remove the node from the tree
        """
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
        """
        Locates a node in the file tree structure.
        
        Args:
            path: Path to the node to find
            
        Returns:
            The found node's contents
        """
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
        """
        Creates the base storage directory for a user.
        
        Raises:
            UserStorageAlreadyExists: If the user's storage directory already exists
        """
        folder_path = Path(self.folder_name)

        if folder_path.exists():
            raise errors.UserStorageAlreadyExists()
        
        folder_path.mkdir()

    def __str__(self):
        """Returns a JSON string representation of the user's file tree."""
        return json.dumps(self.files, indent=4)
