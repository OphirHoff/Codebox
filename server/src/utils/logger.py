import logging
from datetime import datetime
from dotenv import load_dotenv
import os

CONNECTION_LOG_FILE = r"..\logs\connections.log"
WEBSOCKET_ERROR_LOG_FILE = r"..\logs\websocket_errors.log"
GENERAL_ERROR_LOG_FILE = r"..\logs\error.log"
HEADER = f"  | {'Timestamp':<20} | {'Level':<7} | {'Event':<12} | {'Client IP':<15} | {'Port':<5} | {'Data'}\n"
HEADER += '~'*len(HEADER)

class Level:
    LEVEL_INFO = 'INFO'
    LEVEL_WARNING = 'WARNING'
    LEVEL_ERROR = 'ERROR'

class Event:
    SERVER_STARTED = 'SRV_START'
    SERVER_CLOSED = 'SRV_CLOSE'
    CONNECTION_ESTABLISHED = 'CONN_EST'
    CONNECTION_CLOSED = 'DISCONNECT'
    DISCONNECT_FAILED = 'CLOSE_FAILED'
    MESSAGE_SENT = 'MSG_SENT'
    MESSAGE_RECEIVED = 'MSG_RECEIVED'
    EXECUTION_TIMEOUT = 'EXEC_TIMEOUT'
    DB_CONNECTION_ESTABLISHED = 'DB_CONNECT'
    DB_QUERY = 'DB_QUERY'
    DB_RESPONSE = 'DB_RESPONSE'
    GENERAL_SERVER_ERROR = 'SERVER_ERROR'


class Logger:

    def __init__(self, client_ip='N/A', client_port='N/A'):
        self.client_ip = client_ip
        self.client_port = client_port
        load_dotenv()
        self.LOG_TO_CONSOLE = os.getenv("PRINT_NETWORK_LOGS", "false").lower() == "true"

    def configure_logger(self):

        if not os.path.exists(CONNECTION_LOG_FILE) or os.path.getsize(CONNECTION_LOG_FILE) == 0:
            with open(CONNECTION_LOG_FILE, 'w') as log_file:
                # Write the header (column titles)
                log_file.write(HEADER + '\n')
        
        if self.LOG_TO_CONSOLE:
            print(HEADER)
        

        logging.basicConfig(
            filename=CONNECTION_LOG_FILE,
            level=logging.DEBUG,
            format='%(message)s',  # Custom format will be handled manually in the function
        )

        # WebSocket error logger setup
        ws_logger = logging.getLogger("websockets")
        ws_logger.setLevel(logging.ERROR)

        ws_error_handler = logging.FileHandler(WEBSOCKET_ERROR_LOG_FILE, mode='a')
        ws_error_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))

        ws_logger.addHandler(ws_error_handler)
        ws_logger.propagate = False  # Prevent it from printing to console

    def log_connection_event(self, level, event, message='N/A'):
        """
        Logs events related to server-client connections in a structured format.
        """
        # Map log levels to symbols for clarity
        level_symbol = {
            Level.LEVEL_INFO: "[-]",
            Level.LEVEL_WARNING: "[!]",
            Level.LEVEL_ERROR: "[x]"
        }.get(level.upper(), "[-]")  # Default to "[-]" for any unrecognized level

        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        message = message.replace('\n', '')
        log_message = f"{level_symbol} {timestamp:<20} | {level:<7} | {event:<12} | {self.client_ip:<15} | {self.client_port:<5} | {message:.20s}"
        # Log the event based on its level
        log_function = getattr(logging, level.lower(), logging.info)
        log_function(log_message)

        # Optionally print to console
        if self.LOG_TO_CONSOLE:
            print(log_message)