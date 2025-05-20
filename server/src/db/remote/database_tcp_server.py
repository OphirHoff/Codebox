# database_tcp_server.py
import socket
import pickle
import threading
import logging
import sys
import os

# Add the parent directory to sys.path to allow access packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.tcp_by_size import send_one_message, recv_one_message, TCP_DEBUG
from db.database import Database
import errors


DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 65432

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - Server: %(message)s')


def handle_client(conn, addr):
    """
    Handles a single client connection using tcp_by_size for message framing.
    Receives commands, executes them using the db_instance, and sends results.
    """
    logging.info(f"Accepted connection from {addr}")
    active_connection = True
    request_data_for_pickle_error = None # Store data in case of pickle error

    try:

        # Create a new Database instance for this thread.
        db_handler = Database()

        while active_connection: 
            request_data_for_pickle_error = recv_one_message(conn, return_type="bytes")

            if request_data_for_pickle_error is None: 
                logging.info(f"Client {addr} closed connection or error during receive (recv_one_message returned None).")
                active_connection = False
                break 
            
            if not request_data_for_pickle_error: 
                logging.warning(f"Received empty data from {addr} via recv_one_message. This might indicate an issue or an empty message sent by client.")
                continue

            request_payload = pickle.loads(request_data_for_pickle_error)
            logging.info(f"Received from {addr} (via tcp_by_size): command '{request_payload.get('command')}'")

            command = request_payload.get('command')
            args = request_payload.get('args', [])
            kwargs = request_payload.get('kwargs', {})

            response = {}
            try:
                if hasattr(db_handler, command):
                    method_to_call = getattr(db_handler, command)
                    
                    # Special handling for __str__ equivalent if needed
                    if command == 'get_all_users_string': # Matches client
                        result = str(db_handler) # Calls __str__ on Database instance
                    else:
                        result = method_to_call(*args, **kwargs)
                    
                    response['status'] = 'success'
                    response['data'] = result
                    logging.info(f"Command '{command}' executed successfully for {addr}.")
                else:
                    logging.error(f"Unknown command '{command}' from {addr}.")
                    response['status'] = 'error'
                    response['message'] = f"Unknown command: {command}"
                    response['error_type'] = 'UnknownCommandError'
            
            # Catch specific custom errors first
            except errors.UserNotFoundError as e: 
                logging.warning(f"UserNotFoundError for command '{command}' from {addr}: {e}")
                response['status'] = 'error'; response['message'] = str(e); response['error_type'] = type(e).__name__
            # Catch standard Python errors that might occur
            except TypeError as e: # Argument mismatches for called methods
                 logging.error(f"TypeError (argument mismatch?) for command '{command}' from {addr}: {e}")
                 response['status'] = 'error'; response['message'] = f"Argument mismatch or type error for command '{command}': {e}"; response['error_type'] = 'TypeError'
            except Exception as e: # Catch-all for other unexpected errors
                logging.error(f"Unexpected error executing command '{command}' for {addr}: {e}", exc_info=True)
                response['status'] = 'error'; response['message'] = f"An unexpected server error occurred: {str(e)}"; response['error_type'] = type(e).__name__

            serialized_response = pickle.dumps(response)
            
            # Use send_one_message from tcp_by_size.py
            send_one_message(conn, serialized_response)
            logging.debug(f"Sent response to {addr} (via tcp_by_size): {response.get('status')}")
            
            # If you want to handle only one request per connection, uncomment the next line:
            # active_connection = False # This will cause the loop to exit after one request.

    except pickle.UnpicklingError as e:
        logging.error(f"Pickle (Unpickling) error with {addr}: {e}. Data that caused error (first 100 bytes): {request_data_for_pickle_error[:100] if request_data_for_pickle_error else 'None'}", exc_info=True)
        # Optionally send an error response back to client if possible, though connection might be corrupt
    except (socket.error, ConnectionResetError, BrokenPipeError) as e: # Common socket errors
        logging.warning(f"Socket error with {addr}: {e}. Client likely disconnected.")
        active_connection = False # Ensure loop termination
    except EOFError as e: # Can happen if client closes connection while server expects data for unpickling
        logging.warning(f"EOFError with {addr}, likely client closed connection abruptly: {e}")
        active_connection = False
    except Exception as e: # Catch-all for other errors within the handler's main loop
        logging.error(f"Unexpected error in client handler for {addr}: {e}", exc_info=True)
        active_connection = False # Ensure loop termination
    finally:
        if conn:
            logging.info(f"Closing connection for {addr}")
            conn.close()

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
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
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
