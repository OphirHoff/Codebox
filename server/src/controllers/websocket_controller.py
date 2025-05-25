"""
WebSocket Controller for Code Execution Server

This module implements a WebSocket-based server that handles client connections for a secure code execution environment.
It provides functionality for user authentication, file management, and sandboxed Python code execution.

Key Components:
1. Server Class:
   - Manages WebSocket client connections and database connections
   - Handles client registration and authentication
   - Maintains connection pool with database server

2. ClientHandler Class:
   - Handles individual client WebSocket connections
   - Manages sandboxed code execution in Docker containers
   - Handles file operations and user storage
   - Implements real-time code output streaming
   - Manages interactive input/output for running programs

Security Features:
- Sandboxed execution using Docker containers
- Resource limits on containers (CPU, memory, PIDs)
- Network isolation for executed code
- Execution timeout limits
- Base64 encoding for data transfer

Protocol:
- Uses a custom protocol defined in protocol.py for client-server communication
- Supports operations like:
  * User registration and login
  * File creation, reading, updating, deletion
  * Code execution and interactive I/O
  * File downloads and uploads

Dependencies:
- websockets: For WebSocket server implementation
- asyncio: For asynchronous I/O operations
- Docker: For sandboxed code execution
- DatabaseSocketClient: For database operations
"""

import websockets
import asyncio
import os
import json
import protocol
import errors
import traceback

from db.remote.database_socket_client import DatabaseSocketClient

from utils import user_file_manager

from utils.logger import (
    Logger,
    Level,
    Event
    )

from utils.b64 import (
    base64_encode,
    base64_decode
)

# Globals
DB_CLIENTS_NUM = 3
SANDBOX_WORKDIR = '/home/sandboxuser/app'
EXECUTION_TIMEOUT = 60  # seconds

def user_container_id():
    """Generator function that produces unique container IDs."""
    id = 0
    while True:
        id += 1
        yield id

container_id_gen = user_container_id()

class Server:
    """
    WebSocket server that manages client connections and database connections.
    
    This class is responsible for:
    - Managing active WebSocket client connections
    - Maintaining a pool of database connections
    - Handling client authentication and registration
    - Logging server events
    
    Attributes:
        clients (dict): Maps WebSocket connections to user emails
        logger (Logger): Server event logger
        db_server_ip (str): IP address of the database server
        db_connections (list): Pool of database connections
    """

    def __init__(self, db_server_ip):
        """
        Initialize the server with database connection pool.
        
        Args:
            db_server_ip (str): IP address of the database server
        """
        self.clients: dict = {}  # websocket -> email
        self.logger = Logger()
        self.logger.configure_logger()
        self.logger.log_connection_event(Level.LEVEL_INFO, Event.SERVER_STARTED)
        self.db_server_ip = db_server_ip

        # Active connections with DB server
        self.db_connections = [DatabaseSocketClient(self.db_server_ip) for _ in range(DB_CLIENTS_NUM)]

    async def handle_client(self, websocket):
        """
        Handle a new WebSocket client connection.
        
        Creates a ClientHandler instance for the connection and delegates handling to it.
        
        Args:
            websocket (WebSocketServerProtocol): The WebSocket connection to handle
        """
        ip, port = websocket.remote_address
        handler = ClientHandler(websocket, ip, port, self)
        await handler.handle()

    def register_logged_user(self, websocket, email):
        """
        Register an authenticated user's WebSocket connection.
        
        Args:
            websocket (WebSocketServerProtocol): The user's WebSocket connection
            email (str): The user's email address
        """
        self.clients[websocket] = email

    def unregister_user(self, websocket):
        """
        Remove a user's WebSocket connection from the active clients.
        
        Args:
            websocket (WebSocketServerProtocol): The WebSocket connection to remove
        """
        self.clients.pop(websocket, None)

    async def get_db_conn(self):
        """
        Get an available database connection from the pool.
        
        Returns:
            DatabaseSocketClient: An unoccupied database connection
            
        Note:
            This method will block until a connection becomes available
        """
        while True:
            for conn in self.db_connections:
                if not conn.occupied:
                    return conn

    def close(self):
        """
        Close the server and all active client connections.
        
        Logs the closure of each connection and the server shutdown.
        """
        for sock in self.clients:
            try:
                sock.close()
                self.logger.log_connection_event(Level.LEVEL_INFO, Event.CONNECTION_CLOSED, msg=sock.remote_address)
            except websockets.exceptions.WebSocketException:
                self.logger.log_connection_event(Level.LEVEL_ERROR, Event.DISCONNECT_FAILED, msg=sock.remote_address)

        self.logger.log_connection_event(Level.LEVEL_INFO, Event.SERVER_CLOSED)


class ClientHandler:
    """
    Handles individual WebSocket client connections and their operations.
    
    Manages WebSocket communication, authentication, Docker containers for code execution,
    file operations, and real-time code I/O streaming.
    
    Attributes:
        websocket (WebSocketServerProtocol): Client WebSocket connection
        client_ip (str): Client IP address
        client_port (int): Client port number 
        server (Server): Main server instance
        logger (Logger): Client logger
        email (str): User email (set after login)
        container_name (str): Docker container name
        container_running (bool): Container running status
        process (asyncio.subprocess.Process): Running container process
        pid (int): Python script process ID
        process_ready_event (asyncio.Event): Process ready event
    """

    def __init__(self, websocket, ip, port, server):
        """
        Initialize a new client handler.
        
        Args:
            websocket (WebSocketServerProtocol): The client's WebSocket connection
            ip (str): Client's IP address
            port (int): Client's port number
            server (Server): Reference to the main server instance
        """
        self.websocket = websocket
        self.client_ip = ip
        self.client_port = port
        self.server: Server = server
        self.logger = Logger(self.client_ip, self.client_port)
        self.logger.log_connection_event("INFO", "CONN_EST")
        self.email = None  # will be set after login

        self.container_name = f"n-{next(container_id_gen)}"
        self.container_running = None  # Will be set True when container is running
        self.process = None
        self.pid = None

    async def send(self, msg: str) -> None:
        """
        Send a message to the client over WebSocket.
        
        Args:
            msg (str): Message to send
        """
        await self.websocket.send(msg)
        self.logger.log_connection_event(Level.LEVEL_INFO, Event.MESSAGE_SENT, msg[:20])
    
    async def recv(self):
        """
        Receive a message from the client over WebSocket.
        
        Returns:
            str: The received message
        """
        msg = await self.websocket.recv()
        self.logger.log_connection_event(Level.LEVEL_INFO, Event.MESSAGE_RECEIVED, msg[:20])
        return msg

    async def handle(self):
        """
        Main handler loop for client connection.
        
        Continuously receives messages from the client and processes them
        until the connection is closed. Handles cleanup on connection close.
        """
        try:
            while True:
                msg = await self.recv()
                response = await self.handle_request(msg)
                if response:
                    await self.send(response)
        except websockets.exceptions.ConnectionClosed:
            self.logger.log_connection_event(Level.LEVEL_INFO, Event.CONNECTION_CLOSED)
        finally:
            self.server.unregister_user(self.websocket)

    def server_create_response(self, request, data, general_error=False):
        """
        Create a protocol-compliant response message.
        
        Args:
            request (str): The request code being responded to
            data: The response data
            general_error (bool): Whether to return a general error response
        
        Returns:
            str: Protocol-formatted response message
        """
        if request == protocol.CODE_REGISTER:
            if data:  # Registration succeeded
                to_send = protocol.CODE_REGISTER_SUCCESS
            else:  # Registration failed
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_USER_EXIST}"
        
        elif request == protocol.CODE_LOGIN:
            if data:  # Login succeeded
                to_send = f"{protocol.CODE_LOGIN_SUCCESS}~{data}"
            else:  # Login failed
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_LOGIN_FAILED}"
        
        elif request == protocol.CODE_STORAGE_ADD:
            if data:
                to_send = protocol.CODE_STORAGE_UPDATED
            else:
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_STORAGE_CREATE}"

        elif request == protocol.CODE_GET_FILE:
            if data or data == '':  # File exists (data == '' to support empty files)
                encoded_data = base64_encode(data).decode()
                to_send = f"{protocol.CODE_FILE_CONTENT}~{encoded_data}"
            else:  # File wasn't found
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_FILE_NOT_FOUND}"

        elif request == protocol.CODE_SAVE_FILE:
            if data:
                to_send = protocol.CODE_FILE_SAVED
            else:
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_FILE_NOT_FOUND}"

        elif request == protocol.CODE_DELETE_FILE:
            if data:
                to_send = protocol.CODE_FILE_DELETED
            else:
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_FILE_DELETE}"

        elif request == protocol.CODE_DOWNLOAD_FILE:
            if data or data == '':
                encoded_data = base64_encode(data).decode()
                to_send = f"{protocol.CODE_FILE_TO_DOWNLOAD}~{encoded_data}"
            else:
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_FILE_NOT_FOUND}"

        elif request == protocol.CODE_RUN_SCRIPT or request == protocol.CODE_RUN_FILE:
            
            execution_finished, data = data

            if not execution_finished:
                to_send = f"{protocol.CODE_OUTPUT}~{data}"
            else:
                to_send = f"{protocol.CODE_RUN_END}~{data}"
        
        elif request == protocol.CODE_BLOCKED_INPUT:
            to_send = f"{protocol.CODE_BLOCKED_INPUT}"

        if general_error:
            to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_GENERAL}"
        
        return to_send

    async def handle_request(self, msg: str):
        """
        Process an incoming client request.
        
        Parses the request message and dispatches to appropriate handler based on
        the request code.
        
        Args:
            msg (str): The incoming request message
            
        Returns:
            str: Protocol-formatted response message
        """
        fields = msg.split('~')
        code: str = fields[0]
        data: list = fields[1:]

        to_send = ''

        try:
            if code == protocol.CODE_REGISTER:
                email, password = data
                with await self.server.get_db_conn() as db_conn:
                    res = register_user(email, password, db_conn)
                    to_send = self.server_create_response(code, res)
            
            elif code == protocol.CODE_LOGIN:
                email, password = data
                with await self.server.get_db_conn() as db_conn:
                    res = login_user(email, password, db_conn)
                if res:
                    self.server.register_logged_user(self.websocket, email)
                    self.email = email
                to_send = self.server_create_response(code, res)

            elif code == protocol.CODE_GET_FILE:
                with await self.server.get_db_conn() as db_conn:
                    file_content = get_user_file(self.email, data[0], db_conn)
                to_send = self.server_create_response(code, file_content)

            elif code == protocol.CODE_SAVE_FILE:
                data: dict = json.loads(data[0])
                with await self.server.get_db_conn() as db_conn:
                    res = update_user_file(self.email, data["path"], data["content"], db_conn)
                to_send = self.server_create_response(code, res)

            elif code == protocol.CODE_RUN_FILE:
                res = await self.run_from_storage(data[0])
                to_send = self.server_create_response(code, (True, res))
            
            elif code == protocol.CODE_RUN_SCRIPT:
                res = await self.run_script(data[0])
                to_send = self.server_create_response(code, (True, res))

            elif code == protocol.CODE_INPUT:
                return base64_decode(data[0])

            elif code == protocol.CODE_STORAGE_ADD:
                data: dict = json.loads(data[0])
                with await self.server.get_db_conn() as db_conn:
                    res = user_storage_add(self.email, data, db_conn)
                to_send = self.server_create_response(protocol.CODE_STORAGE_ADD, res)
            
            elif code == protocol.CODE_DELETE_FILE:
                file_path = data[0]
                with await self.server.get_db_conn() as db_conn:
                    res = user_file_delete(self.email, file_path, db_conn)
                to_send = self.server_create_response(protocol.CODE_DELETE_FILE, res)

            elif code == protocol.CODE_DOWNLOAD_FILE:
                file_path = data[0]
                with await self.server.get_db_conn() as db_conn:
                    res = get_user_file(self.email, file_path, db_conn)
                to_send = self.server_create_response(protocol.CODE_DOWNLOAD_FILE, res)

        
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            to_send = self.server_create_response(None, None, general_error=True)

        return to_send

    async def run_script(self, data) -> int:
        """
        Execute Python code in a sandboxed Docker container.
        
        Creates a new container with resource limits and security constraints,
        writes the code to a file, and executes it with a timeout. Handles
        real-time output streaming and interactive input.
        
        Args:
            data (str): Base64 encoded Python code to execute
            
        Returns:
            int: Process return code
        """
        # Decode the base64 encoded Python code
        code = base64_decode(data)

        # Build docker command with security constraints:
        # - Limited CPU and memory
        # - Limited number of processes
        # - No network access
        # - Auto-remove container when done
        command = [
            "docker", "run", "-i",
            "--rm",
            "--cpus=0.5",
            "--memory=128m",
            "--pids-limit=64",
            "--network", "none",
            "--name", self.container_name,
            "python_runner",
            "/bin/bash", "-c",
            # Create script file, write code to it, run with timeout
            f"touch script.py && echo '{code}' > script.py && timeout {EXECUTION_TIMEOUT}s python3 -u script.py"
        ]
        
        async def run_process():
            # Start the docker process with pipes for I/O
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self.process = process
            await asyncio.sleep(0.1)  # Wait a bit for the process to start
            # Get the Python process ID inside the container
            self.pid = await self.get_python_pid(self.container_name)

            # Start monitoring input and streaming output concurrently
            await asyncio.gather(
                self.monitor_input(),
                self.stream_output()
            )

            await process.wait()
            return process.returncode

        self.container_running = True

        try:
            # Run the process with a timeout (plus 1 second buffer)
            returncode = await asyncio.wait_for(
                run_process(),
                timeout=EXECUTION_TIMEOUT + 1  # slight buffer
            )
        except asyncio.TimeoutError:
            # Log timeout error and cleanup
            self.logger.log_connection_event(Level.LEVEL_ERROR, Event.EXECUTION_TIMEOUT)
            try:
                self.process.kill()
            except:
                pass
            await self.process.wait()
            return 3

        return returncode

    async def run_from_storage(self, path: str) -> int:
        """
        Execute a Python file from user storage in a sandboxed container.
        
        Similar to run_script() but executes an existing file from the user's
        storage directory. Mounts the storage directory read-only in the container.
        
        Args:
            path (str): Path to the Python file to execute
            
        Returns:
            int: Process return code
        """
        # Get the user's storage directory path
        user_id = self.db_client.get_user_id(self.email)
        user_path = user_file_manager.user_folder_name(user_id)
        
        # Build docker run command with security constraints
        # - Limited CPU and memory
        # - Limited number of processes
        # - No network access
        # - Auto-remove container when done
        command = [
            "docker", "run", "-i",
            "--rm",
            "--cpus=0.5",
            "--memory=128m",
            "--pids-limit=64",
            "--network", "none",
            # Mount user directory read-only into container
            "-v", f"{os.path.abspath(user_path)}:{SANDBOX_WORKDIR}:ro",
            "--name", self.container_name,
            "python_runner",
            "timeout", f"{EXECUTION_TIMEOUT}s", "python3", "-u", path
        ]
        
        async def run_process():
            # Start the docker process with pipes for I/O
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self.process = process
            await asyncio.sleep(0.1)  # Wait a bit for the process to start
            # Get the Python process ID inside the container
            self.pid = await self.get_python_pid(self.container_name, code_path=path)

            # Start monitoring input and streaming output concurrently
            await asyncio.gather(
                self.monitor_input(),
                self.stream_output()
            )

            await process.wait()
            return process.returncode

        self.container_running = True

        try:
            # Run the process with a timeout (plus 1 second buffer)
            returncode = await asyncio.wait_for(
                run_process(),
                timeout=EXECUTION_TIMEOUT + 1  # slight buffer
            )
        except asyncio.TimeoutError:
            # Log timeout error and cleanup
            self.logger.log_connection_event(Level.LEVEL_ERROR, Event.EXECUTION_TIMEOUT)
            self.process.kill()
            await self.process.wait()
            return 3

        return returncode
    
    async def get_python_pid(self, container_name: str, code_path: str = 'script.py') -> int:
        """
        Use `docker exec` to retrieve the PID of the Python process inside the running container.
        """
        # Use `docker exec` to run `pgrep` to get Python execution process id
        command = f"docker exec {container_name} pgrep -f {code_path}"
        
        async def run_pgrep():
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Read the output from the command
            pid = await process.stdout.readline()
            await process.wait()

            return pid
        

        while self.is_process_running():
            pid = await run_pgrep()
            pid_str = pid.strip().decode('utf-8')  # decode bytes to string
            if pid_str:
                try:
                    return int(pid_str)  # Convert the PID string to an integer
                except ValueError:
                    self.logger.log_connection_event(Level.LEVEL_ERROR, Event.GENERAL_SERVER_ERROR, message="Failed to fetch pid.")
                    return None

    async def stream_output(self):
        """
        Streams process output from Docker container to WebSocket client.
        
        Reads stdout in 1024-byte chunks, base64-encodes the data, and sends
        it to the client until EOF is reached. Performs cleanup on completion.
        """
        while True:
            # Read chunk from stdout
            chunk = await self.process.stdout.read(1024)
            if not chunk:
                break  # EOF reached
            
            # Encode in base64 format
            encoded_line = base64_encode(chunk.decode()).decode('utf-8')

            # Send to client
            await self.send(self.server_create_response(protocol.CODE_RUN_SCRIPT, (False, encoded_line)))
        
        await self.process.wait()
        self.container_running = False
    
    async def monitor_input(self):
        """
        Monitors the running container process for input blocking state.
        
        Continuously polls the process state using `ps` command to detect when
        the process enters sleep state ('S'), indicating it's waiting for stdin.
        Triggers input streaming when blocking is detected.
        
        Runs until container execution completes.
        """

        # Command to run in shell
        command = f"docker exec {self.container_name} ps -o state= -p {self.pid}"

        while self.container_running:
            
            # Run command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Read command execution output
            res = await process.stdout.read()
            if res.decode().strip() == 'S':
                await self.stream_input()
            
    async def stream_input(self):
        """
        Handles user input streaming to the blocked container process.
        
        Notifies the client that input is required, receives input from WebSocket,
        and forwards it to the container's stdin via process file descriptor.
        Ensures proper newline termination for input processing.
        """
        # Inform client that input is required
        await self.send(self.server_create_response(protocol.CODE_BLOCKED_INPUT, None))

        # Get input entered by user
        input = await self.handle_request(await self.recv())

        # Command to write to process's stdin in the container
        command = [
            "docker", "exec", "-i", self.container_name,
            "bash", "-c", f"cat > /proc/{self.pid}/fd/0"
        ]

        # Run command
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Make sure input ends with new-line
        if not input.endswith('\n'):
            input += '\n'

        # Send the input string
        await process.communicate(input.encode())

    def is_process_running(self):
        return self.process.returncode is None


def register_user(email: str, password: str, db_conn: DatabaseSocketClient) -> bool:
    """
    Register a new user in the system.
    
    Creates a new user account with the given email and password,
    and initializes their file storage structure.
    
    Args:
        email (str): User's email address
        password (str): User's password
        db_conn (DatabaseSocketClient): Database connection to use
        
    Returns:
        bool: True if registration successful, False if user already exists
    """
    regi_success = db_conn.add_user(email, password)

    if regi_success:
        user_id: int = db_conn.get_user_id(email)
        user_storage = user_file_manager.UserStorage(user_id)
        db_conn.set_user_files_struct(email, user_storage)
        return True
    
    return False


def login_user(email: str, password: str, db_conn: DatabaseSocketClient) -> str | bool:
    """
    Authenticate a user and retrieve their file structure.
    
    Args:
        email (str): User's email address
        password (str): User's password
        db_conn (DatabaseSocketClient): Database connection to use
        
    Returns:
        str | bool: JSON string of user's file hierarchy if login successful,
                   False if login failed
    """
    try:
        if db_conn.is_password_ok(email, password):
            user_storage: user_file_manager.UserStorage = db_conn.get_user_files_struct(email)
            return str(user_storage)
        return False
    
    except Exception as err:
        # Login failed
        print(f"Error: {err}")
        return False


def user_storage_add(email, new_node: str, db_conn: DatabaseSocketClient) -> bool:
    """
    Add a new file or folder to user's storage.
    
    Args:
        email (str): User's email address
        new_node (str): JSON object describing the new file/folder
        db_conn (DatabaseSocketClient): Database connection to use
        
    Returns:
        bool: True if creation successful, False otherwise
    """
    user_storage: user_file_manager.UserStorage = db_conn.get_user_files_struct(email)

    create_type: str = new_node[protocol.JsonEntries.NODE_TYPE]
    path: str = new_node[protocol.JsonEntries.NODE_PATH]

    try:
        if create_type == user_file_manager.FileType.FILE.value:
            user_storage.create_file(path)
        elif create_type == user_file_manager.FileType.FOLDER.value:
            user_storage.create_dir(path)
        else:
            raise errors.InvalidEntry(protocol.JsonEntries.NODE_TYPE, create_type)
    except Exception:
        # Storage update failed
        return False
    
    db_conn.set_user_files_struct(email, user_storage)

    # Storage update succeeded
    return True


def user_file_delete(email, file_path: str, db_conn: DatabaseSocketClient) -> bool:
    """
    Delete a file from user's storage.
    
    Args:
        email (str): User's email address
        file_path (str): Path to the file to delete
        db_conn (DatabaseSocketClient): Database connection to use
        
    Returns:
        bool: True if deletion successful, False otherwise
    """
    user_storage: user_file_manager.UserStorage = db_conn.get_user_files_struct(email)

    try:
        user_storage.delete_file(file_path)
    except Exception as e:
        print(f"error: {e}")
        # Storage update failed
        return False

    db_conn.set_user_files_struct(email, user_storage)

    # Storage update succeeded
    return True


def user_rename_file(email, old_path, new_path, db_conn: DatabaseSocketClient) -> bool:
    """
    Rename a file in user's storage.
    
    Args:
        email (str): User's email address
        old_path (str): Current path of the file
        new_path (str): New path for the file
        db_conn (DatabaseSocketClient): Database connection to use
        
    Returns:
        bool: True if rename successful, False otherwise
    """
    user_storage: user_file_manager.UserStorage = db_conn.get_user_files_struct(email)

    try:
        user_storage.rename_file(old_path, new_path)
    except Exception as e:
        print(f"error: {e}")
        # File rename failed
        return False

    db_conn.set_user_files_struct(email, user_storage)

    # File rename succeeded
    return True


def get_user_file(email, path: str, db_conn: DatabaseSocketClient) -> str | bool:
    """
    Retrieve contents of a file from user's storage.
    
    Args:
        email (str): User's email address
        path (str): Path to the file
        db_conn (DatabaseSocketClient): Database connection to use
        
    Returns:
        str | bool: File contents if successful, False if file not found
    """
    user_id = db_conn.get_user_id(email)

    try:
        file_content = user_file_manager.get_file_content(user_id, path)
        return file_content
    except Exception as e:
        print(f"error: {e}")
        return False


def update_user_file(email, path: str, new_content: str, db_conn: DatabaseSocketClient) -> bool:
    """
    Update the contents of a file in user's storage.
    
    Args:
        email (str): User's email address
        path (str): Path to the file
        new_content (str): New content for the file
        db_conn (DatabaseSocketClient): Database connection to use
        
    Returns:
        bool: True if update successful, False if file not found
    """
    user_id = db_conn.get_user_id(email)

    try:
        user_file_manager.update_file_content(user_id, path, new_content)
        return True
    except Exception as e:
        print(f"error: {e}")
    