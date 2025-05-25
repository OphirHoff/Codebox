"""
Secure database client implementation using encrypted socket communication.

This module provides a secure client for remote database operations using:
1. TCP sockets with message framing
2. Hybrid RSA/AES encryption:
   - RSA for initial AES key exchange
   - AES for ongoing secure communication
3. Pickle for data serialization
4. Structured logging of all operations

Security Features:
- RSA public key infrastructure for key exchange
- AES-256 session encryption
- Secure connection establishment protocol
- Connection timeout handling

Communication Protocol:
1. Initial Connection:
   - Client connects to server
   - Generates AES session key
   - Encrypts AES key with server's RSA public key
   - Sends encrypted key to server
   - Receives confirmation

2. Database Operations:
   - Commands sent as encrypted pickled dictionaries
   - Server responses include status and data/error info
   - All messages framed using tcp_by_size protocol

Connection Management:
- Context manager support for safe resource handling
- Automatic connection cleanup
- Connection state tracking
- Timeout handling

Default Configuration:
    Host: localhost
    Port: 65432
    Timeout: 10 seconds

Requirements:
    - Server's RSA public key must be available
    - TCP connectivity to database server
    - Proper security certificates
"""

import socket
import pickle
import logging
import traceback
from utils.tcp_by_size import send_one_message, recv_one_message, TCP_DEBUG
from utils.user_file_manager import UserStorage

from utils.secure_connection import (
    load_rsa_public_key,
    rsa_encrypt,
    gen_aes_key,
    send_secure, 
    recv_secure
)

from utils.logger import (
    Logger,
    Level,
    Event
    )

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 65432

class DatabaseSocketClient:
    """
    A client for interacting with the database server over TCP sockets,
    using tcp_by_size for message framing.
    """
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        """
        Initializes the DatabaseSocketClient.

        Args:
            host (str): The hostname or IP address of the database server.
            port (int): The port number of the database server.
        """
        self.host = host
        self.port = port
        self.sock = None
        self.aes_key = None
        self.timeout = 10 # seconds
        self.logger = Logger(self.host, self.port)
        self.occupied = False  # Is the connection currently being used

        self._init_connection()
        self._establish_secured_connection()

    def _init_connection(self):
        """Initialize TCP socket and connect to server."""
        try:
            self.sock = socket.socket()
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
        except Exception as err:
            self.logger.log_connection_event(Level.LEVEL_ERROR, Event.DB_CONNECTION_FAILED, message=err)

    def close_connection(self):
        """Safely close the connection."""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                # Socket already closed or not connected
                pass
            finally:
                try:
                    self.sock.close()
                except Exception:
                    pass

    def _establish_secured_connection(self):
        """
        Establishes a secured connection with server using AES for data encryption,
        and RSA for key exchanging.
        """
        # Generate an AES key for the session
        self.aes_key = gen_aes_key()

        # Load RSA public key from storage
        public_key = load_rsa_public_key()

        # Encrypt AES key using the RSA public key
        enc_rsa_key = rsa_encrypt(self.aes_key, public_key)

        msg = {
            'aes_key': enc_rsa_key
        }

        serialized_msg = pickle.dumps(msg)

        # Send encrypted AES key to server
        send_one_message(self.sock, serialized_msg)

        # Receive server response
        received_data = recv_one_message(self.sock, return_type='bytes')
        response = pickle.loads(received_data)

        if response.get('status') == 'success':
            self.logger.log_connection_event(Level.LEVEL_INFO, Event.DB_CONNECTION_ESTABLISHED)
        else:
            self.logger.log_connection_event(Level.LEVEL_ERROR, Event.DB_CONNECTION_FAILED)

    def _send_request(self, command, *args, **kwargs):
        """
        Sends a request to the database server and returns the response.
        Uses functions from tcp_by_size.py for sending and receiving.

        Args:
            command (str): The command to execute on the server (e.g., 'add_user').
            *args: Positional arguments for the command.
            **kwargs: Keyword arguments for the command.

        Returns:
            The result from the server.

        Raises:
            ConnectionError: If there's an issue connecting to or communicating with the server.
            ServerError: If the server indicates an error processing the command.
        """
        request_payload = {
            'command': command,
            'args': args,
            'kwargs': kwargs
        }
        
        try:
            serialized_payload = pickle.dumps(request_payload)
            
            send_secure(self.sock, serialized_payload, self.aes_key)
            self.logger.log_connection_event(Level.LEVEL_INFO, Event.DB_QUERY, message=f"{command} with args: {args}, kwargs: {kwargs}")

            # received_data = recv_one_message(sock, return_type="bytes")
            received_data = recv_secure(self.sock, self.aes_key)
            
            if received_data is None: # Connection closed or error in recv_one_message
                logging.error("Server closed connection or error during receive.")
                raise ConnectionError("Server closed connection or error during receive.")
            if not received_data: # Empty response might be an issue
                logging.warning("Received empty data from server.")
                # Depending on protocol, empty might be valid or an error indicator
                # For now, assume it might lead to pickle error if not handled
                raise ConnectionError("Received empty data from server, cannot unpickle.")

            response = pickle.loads(received_data)
            self.logger.log_connection_event(Level.LEVEL_INFO, Event.DB_RESPONSE, message=f"{response.get('status')}")

            if response.get('status') == 'success':
                return response.get('data')
            elif response.get('status') == 'error':
                error_type = response.get('error_type', 'UnknownError')
                error_message = response.get('message', 'Unknown server error')
                logging.error(f"Server error: {error_type} - {error_message}")
                # raise ServerError(f"{error_type}: {error_message}")
            else:
                logging.error(f"Unknown response format: {response}")
                raise ConnectionError("Unknown response format from server.")
        
        except Exception as err:
            self.logger.log_connection_event(Level.LEVEL_ERROR, Event.DB_QUERY_FAILED)
            print(traceback.format_exc())

    def is_user_exist(self, email):
        """Checks if a user exists."""
        return self._send_request('is_user_exist', email)

    def get_user_id(self, email):
        """Gets the user ID for a given email."""
        return self._send_request('get_user_id', email)

    def is_password_ok(self, email, password):
        """Checks if the provided password is correct for the user."""
        return self._send_request('is_password_ok', email, password)

    def add_user(self, email, password, storage_struct='[]', verf_code=None):
        """Adds a new user."""
        return self._send_request('add_user', email, password, storage_struct=storage_struct, verf_code=verf_code)

    def set_user_files_struct(self, email, storage_struct: UserStorage):
        """Sets the user's file structure."""
        return self._send_request('set_user_files_struct', email, storage_struct)

    def get_user_files_struct(self, email) -> UserStorage:
        """Gets the user's file structure."""
        return self._send_request('get_user_files_struct', email)
    
    def get_all_users_string(self):
        """Gets a string representation of all users (for debugging/info)."""
        return self._send_request('get_all_users_string')
    
    def __enter__(self):
        self.occupied = True
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.occupied = False