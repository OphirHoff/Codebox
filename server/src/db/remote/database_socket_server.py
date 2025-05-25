"""
Multi-threaded database server with secure socket communication.

Features:
- Thread-safe database operations
- RSA/AES encrypted connections
- Client session management
- Structured error handling and logging

Protocol:
- RSA private key for AES key decryption
- AES for secure command execution
- Pickled response serialization

Configuration:
    Host: 0.0.0.0 (all interfaces)
    Port: 65432
    Max Connections: 5
"""
import socket
import pickle
import threading
import logging
import sys
import os

# Add the parent directory to sys.path to allow access packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.tcp_by_size import send_one_message, recv_one_message

from utils.secure_connection import (
    load_rsa_private_key,
    rsa_decrypt,
    send_secure,
    recv_secure
)

from db.database import Database, db_lock
import errors


DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 65432

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - Server: %(message)s')

class ClientHandler:

    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.aes_key = None

    def _establish_secured_connection(self):
        """
        Establishes a secured connection with client using AES for data encryption,
        and RSA for key exchanging.
        """
        # Receive encrypted AES key from client
        msg = recv_one_message(self.conn, return_type='bytes')
        data = pickle.loads(msg)
        enc_aes_key = data.get('aes_key')

        # Load RSA private key from storage
        rsa_private_key = load_rsa_private_key()

        # Decrypt and store encrypted AES key
        self.aes_key = rsa_decrypt(enc_aes_key, rsa_private_key)

        # Inform client on success
        to_send = {
            'status': 'success'
        }

        send_one_message(self.conn, pickle.dumps(to_send))

    def handle_client(self):
        """
        Handles a single client connection using tcp_by_size for message framing.
        Receives commands, executes them using the db_instance, and sends results.
        """
        logging.info(f"Accepted connection from {self.addr}")
        active_connection = True
        request_data_for_pickle_error = None # Store data in case of pickle error

        try:

            self._establish_secured_connection()

            # Create a new Database instance for this thread.
            db_handler = Database()

            while active_connection: 
                # request_data_for_pickle_error = recv_one_message(self.conn, return_type="bytes")
                request_data_for_pickle_error = recv_secure(self.conn, self.aes_key)

                if request_data_for_pickle_error is None: 
                    logging.info(f"Client {self.addr} closed connection or error during receive (recv_one_message returned None).")
                    active_connection = False
                    break 
                
                if not request_data_for_pickle_error: 
                    logging.warning(f"Received empty data from {self.addr} via recv_one_message. This might indicate an issue or an empty message sent by client.")
                    continue

                request_payload = pickle.loads(request_data_for_pickle_error)
                logging.info(f"Received from {self.addr} (via tcp_by_size): command '{request_payload.get('command')}'")

                command = request_payload.get('command')
                args = request_payload.get('args', [])
                kwargs = request_payload.get('kwargs', {})

                response = {}
                try:
                    if hasattr(db_handler, command):
                        method_to_call = getattr(db_handler, command)
                        
                        with db_lock:
                            # Special handling for __str__ equivalent if needed
                            if command == 'get_all_users_string': # Matches client
                                result = str(db_handler) # Calls __str__ on Database instance
                            else:
                                result = method_to_call(*args, **kwargs)
                        
                        response['status'] = 'success'
                        response['data'] = result
                        logging.info(f"Command '{command}' executed successfully for {self.addr}.")
                    else:
                        logging.error(f"Unknown command '{command}' from {self.addr}.")
                        response['status'] = 'error'
                        response['message'] = f"Unknown command: {command}"
                        response['error_type'] = 'UnknownCommandError'
                
                # Catch specific custom errors first
                except errors.UserNotFoundError as e: 
                    logging.warning(f"UserNotFoundError for command '{command}' from {self.addr}: {e}")
                    response['status'] = 'error'; response['message'] = str(e); response['error_type'] = type(e).__name__
                # Catch standard Python errors that might occur
                except TypeError as e: # Argument mismatches for called methods
                    logging.error(f"TypeError (argument mismatch?) for command '{command}' from {self.addr}: {e}")
                    response['status'] = 'error'; response['message'] = f"Argument mismatch or type error for command '{command}': {e}"; response['error_type'] = 'TypeError'
                except Exception as e: # Catch-all for other unexpected errors
                    logging.error(f"Unexpected error executing command '{command}' for {self.addr}: {e}", exc_info=True)
                    response['status'] = 'error'; response['message'] = f"An unexpected server error occurred: {str(e)}"; response['error_type'] = type(e).__name__

                serialized_response = pickle.dumps(response)
                
                # Use send_one_message from tcp_by_size.py
                # send_one_message(self.conn, serialized_response)
                send_secure(self.conn, serialized_response, self.aes_key)
                logging.debug(f"Sent response to {self.addr} (via tcp_by_size): {response.get('status')}")

        except pickle.UnpicklingError as e:
            logging.error(f"Pickle (Unpickling) error with {self.addr}: {e}. Data that caused error (first 100 bytes): {request_data_for_pickle_error[:100] if request_data_for_pickle_error else 'None'}", exc_info=True)
            # Optionally send an error response back to client if possible, though connection might be corrupt
        except (socket.error, ConnectionResetError, BrokenPipeError) as e: # Common socket errors
            logging.warning(f"Socket error with {self.addr}: {e}. Client likely disconnected.")
            active_connection = False # Ensure loop termination
        except EOFError as e: # Can happen if client closes connection while server expects data for unpickling
            logging.warning(f"EOFError with {self.addr}, likely client closed connection abruptly: {e}")
            active_connection = False
        except Exception as e: # Catch-all for other errors within the handler's main loop
            logging.error(f"Unexpected error in client handler for {self.addr}: {e}", exc_info=True)
            active_connection = False # Ensure loop termination
        finally:
            if self.conn:
                logging.info(f"Closing connection for {self.addr}")
                self.conn.close()

def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """
    Starts the TCP server to listen for database commands.
    """
    server_socket = socket.socket()
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5) # Listen for up to 5 queued connections
        logging.info(f"Database server (using tcp_by_size) listening on {host}:{port}")

        while True:
            try:
                conn, addr = server_socket.accept()
                client_handler = ClientHandler(conn, addr)
                client_thread = threading.Thread(target=client_handler.handle_client)
                client_thread.daemon = True # Daemon threads will exit when the main program exits.
                client_thread.start()
            except Exception as e: # Catch errors during accept or thread creation
                logging.error(f"Error accepting connection or starting thread: {e}", exc_info=True)
    
    except OSError as e: # Errors like "address already in use"
        logging.critical(f"Server could not bind to {host}:{port}. Error: {e}")
    except KeyboardInterrupt:
        logging.info("Server shutting down due to KeyboardInterrupt.")
    except Exception as e: # Catch-all for critical errors in the server's main setup/loop
        logging.critical(f"A critical error occurred in server main loop: {e}", exc_info=True)
    finally:
        logging.info("Closing server socket.")
        if server_socket:
            server_socket.close()

if __name__ == '__main__':

    start_server()
