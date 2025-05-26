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
    def __init__(self, client_socket: socket.socket, client_address):
        self.socket = client_socket
        self.addr = client_address
        self.aes_key = None

    def _establish_secured_connection(self):
        """
        Establishes a secured connection with client using AES for data encryption,
        and RSA for key exchanging.
        """
        try:
            # Receive encrypted AES key from client
            msg = recv_one_message(self.socket, return_type='bytes')
            if not msg:
                raise ConnectionError("Failed to receive AES key from client")

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

            send_one_message(self.socket, pickle.dumps(to_send))
            
        except Exception as e:
            logging.error(f"Error establishing secure connection with {self.addr}: {e}")
            raise

    def handle_client(self):
        """
        Handles a single client connection using synchronous socket operations.
        Receives commands, executes them using the db_instance, and sends results.
        """
        logging.info(f"Accepted connection from {self.addr}")
        active_connection = True

        try:
            self._establish_secured_connection()

            # Create a new Database instance for this client
            db_handler = Database()

            while active_connection:
                try:
                    # Receive request
                    request_data = recv_secure(self.socket, self.aes_key)
                    
                    if request_data is None:
                        logging.info(f"Client {self.addr} closed connection.")
                        break

                    request_payload = pickle.loads(request_data)
                    logging.info(f"Received from {self.addr}: command '{request_payload.get('command')}'")

                    command = request_payload.get('command')
                    args = request_payload.get('args', [])
                    kwargs = request_payload.get('kwargs', {})

                    response = {}
                    try:
                        if hasattr(db_handler, command):
                            method_to_call = getattr(db_handler, command)
                            
                            with db_lock:
                                # Special handling for __str__ equivalent
                                if command == 'get_all_users_string':
                                    result = str(db_handler)
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
                    
                    except errors.UserNotFoundError as e:
                        logging.warning(f"UserNotFoundError for command '{command}' from {self.addr}: {e}")
                        response['status'] = 'error'
                        response['message'] = str(e)
                        response['error_type'] = type(e).__name__
                    except TypeError as e:
                        logging.error(f"TypeError for command '{command}' from {self.addr}: {e}")
                        response['status'] = 'error'
                        response['message'] = f"Argument mismatch or type error for command '{command}': {e}"
                        response['error_type'] = 'TypeError'
                    except Exception as e:
                        logging.error(f"Unexpected error executing command '{command}' for {self.addr}: {e}", exc_info=True)
                        response['status'] = 'error'
                        response['message'] = f"An unexpected server error occurred: {str(e)}"
                        response['error_type'] = type(e).__name__

                    # Send response
                    send_secure(self.socket, pickle.dumps(response), self.aes_key)
                    logging.debug(f"Sent response to {self.addr}: {response.get('status')}")

                except (pickle.UnpicklingError, EOFError) as e:
                    logging.error(f"Error processing request from {self.addr}: {e}")
                    break

        except Exception as e:
            logging.error(f"Unexpected error in client handler for {self.addr}: {e}", exc_info=True)
        finally:
            try:
                self.socket.close()
                logging.info(f"Closed connection for {self.addr}")
            except Exception as e:
                logging.error(f"Error closing connection for {self.addr}: {e}")

def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """
    Starts the TCP server to listen for database commands.
    Uses threading to handle multiple clients.
    """
    try:
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        
        logging.info(f'Database server listening on {host}:{port}')

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                client_handler = ClientHandler(client_socket, client_address)
                client_thread = threading.Thread(target=client_handler.handle_client)
                client_thread.daemon = True # Daemon threads will exit when the main program exits.
                client_thread.start()
            except Exception as e:
                logging.error(f"Error accepting client connection: {e}")
            
    except OSError as e:
        logging.critical(f"Server could not bind to {host}:{port}. Error: {e}")
    except KeyboardInterrupt:
        logging.info("Server shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logging.critical(f"A critical error occurred in server main loop: {e}", exc_info=True)
    finally:
        try:
            server_socket.close()
        except:
            pass

if __name__ == '__main__':
    start_server()
