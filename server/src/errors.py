"""
Custom exception classes for handling specific application errors.

This module defines a hierarchy of custom exceptions used throughout the application
to handle various error scenarios in a structured way.
"""

class CustomError(Exception):
    """Base class for all custom exceptions in the application."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class InvalidRequestCodeError(CustomError):
    """Raised when an unrecognized request code is received from client."""
    def __init__(self, message="Received invalid request code from client."):
        super().__init__(message)

class UserNotFoundError(CustomError):
    """Raised when attempting to access a non-existent user account."""
    def __init__(self, email):
        super().__init__(f"No user found with email '{email}'")

class UserStorageAlreadyExists(CustomError):
    """Raised when attempting to create storage for a user that already has one."""
    def __init__(self, message="Tried to create storage folder that already exists."):
        super().__init__(message)

class FileAlreadyExists(CustomError):
    """Raised when attempting to create a file at a path that is already occupied."""
    def __init__(self, path):
        super().__init__(f"Tried to create file ({path}) which already exists.")

class FolderAlreadyExists(CustomError):
    """Raised when attempting to create a directory at a path that is already occupied."""
    def __init__(self, path):
        super().__init__(f"Tried to create folder ({path}) which already exists.")

class InvalidEntry(CustomError):
    """Raised when encountering invalid entries in JSON/dictionary data structures."""
    def __init__(self, entry, value):
        super().__init__(f"Invalid Json/dictionary entry encountered - {entry}: {value}")