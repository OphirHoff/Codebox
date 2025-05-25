"""
Structured logging system for server operations and connections.

This module implements a comprehensive logging system that provides:
- Structured log format with consistent columns
- Multiple log files for different concerns
- WebSocket-specific error logging
- Optional console output (controlled via environment)

Log Files:
    ../logs/
        connections.log    - Main connection and operation logs
        websocket_errors.log - WebSocket-specific errors
        error.log         - General error logging

Log Format:
    | Timestamp          | Level   | Event      | Client IP    | Port  | Data
    Example:
    [-] 2024-01-01T12:00:00Z | INFO    | CONN_EST   | 192.168.1.1   | 8080  | Connected

Environment Variables:
    PRINT_NETWORK_LOGS: "true"/"false" - Enable console output of logs
"""

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
    """Log level constants for consistent level naming."""
    LEVEL_INFO = 'INFO'
    LEVEL_WARNING = 'WARNING'
    LEVEL_ERROR = 'ERROR'

class Event:
    """
    Event type constants for standardized event logging.
    
    Server Events:
        SRV_START/CLOSE - Server lifecycle events
        CONN_EST/DISCONNECT - Connection handling
        
    Message Events:
        MSG_SENT/RECEIVED - Communication logging
        EXEC_TIMEOUT - Script execution issues
        
    Database Events:
        DB_CONNECT/CONN_ERR - Database connection status
        DB_QUERY/RESPONSE - Database operations
        DB_QUERY_F - Failed database operations
        
    Error Events:
        SERVER_ERROR - General server issues
    """
    SERVER_STARTED = 'SRV_START'
    SERVER_CLOSED = 'SRV_CLOSE'
    CONNECTION_ESTABLISHED = 'CONN_EST'
    CONNECTION_CLOSED = 'DISCONNECT'
    DISCONNECT_FAILED = 'CLOSE_FAILED'
    MESSAGE_SENT = 'MSG_SENT'
    MESSAGE_RECEIVED = 'MSG_RECEIVED'
    EXECUTION_TIMEOUT = 'EXEC_TIMEOUT'
    DB_CONNECTION_ESTABLISHED = 'DB_CONNECT'
    DB_CONNECTION_FAILED = 'DB_CONN_ERR'
    DB_QUERY = 'DB_QUERY'
    DB_RESPONSE = 'DB_RESPONSE'
    DB_QUERY_FAILED = 'DB_QUERY_F'
    GENERAL_SERVER_ERROR = 'SERVER_ERROR'


class Logger:
    """
    Structured logger for server operations with consistent formatting.
    
    Features:
    - Configurable console output
    - Structured log format
    - Multiple log destinations
    - Level-based formatting
    """

    def __init__(self, client_ip='N/A', client_port='N/A'):
        """
        Initialize logger with client information.

        Args:
            client_ip: IP address of the client (default: 'N/A')
            client_port: Port number of the client connection (default: 'N/A')
        """
        self.client_ip = client_ip
        self.client_port = client_port
        load_dotenv()
        self.LOG_TO_CONSOLE = os.getenv("PRINT_NETWORK_LOGS", "false").lower() == "true"

    def configure_logger(self):
        """
        Configure logging system with file handlers and formatters.
        
        - Creates log files if they don't exist
        - Sets up WebSocket error logging
        - Configures console output if enabled
        """
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
        Log a connection event with consistent formatting.

        Args:
            level: Log level from Level class
            event: Event type from Event class
            message: Additional event information (default: 'N/A')
            
        Format:
            [symbol] timestamp | level | event | client_ip | port | message
            
        Symbols:
            [-] Info
            [!] Warning
            [x] Error
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