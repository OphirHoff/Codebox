import websockets
import requests
import asyncio
import base64
import os
import json
import protocol
from db import database
from utils import user_file_manager
import errors
import traceback
from utils.logger import (
    Logger,
    Level,
    Event
    )

# Globals
db = database.Database()
SANDBOX_WORKDIR = '/home/sandboxuser/app'
EXECUTION_TIMEOUT = 10  # seconds

def user_container_id():

    id = 0
    while True:
        id += 1
        yield id

container_id_gen = user_container_id()

class Server:
    def __init__(self, port):
        self.server_ip = requests.get('https://ifconfig.me').text
        self.server_port = port
        self.clients: dict = {}  # websocket -> email
        self.logger = Logger()
        self.logger.configure_logger()
        self.logger.log_connection_event(Level.LEVEL_INFO, Event.SERVER_STARTED)

    async def handle_client(self, websocket):
        ip, port = websocket.remote_address
        handler = ClientHandler(websocket, ip, port, self)
        await handler.handle()

    def register_logged_user(self, websocket, email):
        self.clients[websocket] = email

    def unregister_user(self, websocket):
        self.clients.pop(websocket, None)

    def close(self):

        for sock in self.clients:
            try:
                sock.close()
                self.logger.log_connection_event(Level.LEVEL_INFO, Event.CONNECTION_CLOSED, msg=sock.remote_address)
            except websockets.exceptions.WebSocketException:
                self.logger.log_connection_event(Level.LEVEL_ERROR, Event.DISCONNECT_FAILED, msg=sock.remote_address)

        self.logger.log_connection_event(Level.LEVEL_INFO, Event.SERVER_CLOSED)


class ClientHandler:
    def __init__(self, websocket, ip, port, server):
        self.websocket = websocket
        self.client_ip = ip
        self.client_port = port
        self.server: Server = server
        self.logger = Logger(self.client_ip, self.client_port)
        self.logger.log_connection_event("INFO", "CONN_EST")
        self.email = None  # will be set after login

        # self.container_name = f"{self.client_ip.replace('.', '-')}-{self.client_port}"
        self.container_name = f"n-{next(container_id_gen)}"
        self.container_running = None  # Will be set True when container is running
        self.process = None
        self.pid = None
        self.process_ready_event = asyncio.Event()

    async def send(self, msg: str) -> None:
        await self.websocket.send(msg)
        self.logger.log_connection_event(Level.LEVEL_INFO, Event.MESSAGE_SENT, msg[:4])
    
    async def recv(self):
        msg = await self.websocket.recv()
        self.logger.log_connection_event(Level.LEVEL_INFO, Event.MESSAGE_RECEIVED, msg[:20])
        
        return msg

    async def handle(self):
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
        
        fields = msg.split('~')
        code: str = fields[0]
        data: list = fields[1:]

        to_send = ''

        try:
            if code == protocol.CODE_REGISTER:
                email, password = data
                res = register_user(email, password)
                to_send = self.server_create_response(code, res)
            
            elif code == protocol.CODE_LOGIN:
                email, password = data
                res = login_user(email, password)
                if res:
                    self.server.register_logged_user(self.websocket, email)
                    self.email = email
                to_send = self.server_create_response(code, res)

            elif code == protocol.CODE_GET_FILE:
                to_send = self.server_create_response(code, get_user_file(self.email, data[0]))

            elif code == protocol.CODE_SAVE_FILE:
                data: dict = json.loads(data[0])
                to_send = self.server_create_response(code, update_user_file(self.email, data["path"], data["content"]))

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
                res = user_storage_add(self.email, data)
                to_send = self.server_create_response(protocol.CODE_STORAGE_ADD, res)
            
            elif code == protocol.CODE_DELETE_FILE:
                file_path = data[0]
                res = user_file_delete(self.email, file_path)
                to_send = self.server_create_response(protocol.CODE_DELETE_FILE, res)

        
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            to_send = self.server_create_response(None, None, general_error=True)

        return to_send

    async def run_script(self, data) -> int:

        code = base64_decode(data)

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
            f"touch script.py && echo '{code}' > script.py && timeout {EXECUTION_TIMEOUT}s python3 -u script.py"
        ]
        
        async def run_process():
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self.process = process
            await asyncio.sleep(0.1)  # Wait a bit for the process to start
            self.pid = await self.get_python_pid(self.container_name)

            # Signal that the process is ready
            self.process_ready_event.set()  # To fix - event not needed anymore

            await asyncio.gather(
                self.moniter_input_syscalls(),
                self.stream_output()
            )

            await process.wait()
            return process.returncode

        self.container_running = True

        try:
            returncode = await asyncio.wait_for(
                run_process(),
                timeout=EXECUTION_TIMEOUT + 1  # slight buffer
            )
        except asyncio.TimeoutError:
            self.logger.log_connection_event(Level.LEVEL_ERROR, Event.EXECUTION_TIMEOUT)
            try:
                self.process.kill()
            except:
                pass
            await self.process.wait()
            return 3

        return returncode

    async def run_from_storage(self, path: str) -> int:
        
        user_id = db.get_user_id(self.email)
        user_path = user_file_manager.user_folder_name(user_id)
        
        command = [
            "docker", "run", "-i",
            "--rm",
            "--cpus=0.5",
            "--memory=128m",
            "--pids-limit=64",
            "--network", "none",
            "-v", f"{os.path.abspath(user_path)}:{SANDBOX_WORKDIR}:ro",
            "--name", self.container_name,
            "python_runner",
            f"timeout {EXECUTION_TIMEOUT}s", "python3", "-u", path
        ]
        
        async def run_process():
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self.process = process
            await asyncio.sleep(0.1)  # Wait a bit for the process to start
            self.pid = await self.get_python_pid(self.container_name)

            # Signal that the process is ready
            self.process_ready_event.set()  # To fix - event not needed anymore

            await asyncio.gather(
                self.moniter_input_syscalls(),
                self.stream_output()
            )

            await process.wait()
            return process.returncode

        self.container_running = True

        try:
            returncode = await asyncio.wait_for(
                run_process(),
                timeout=EXECUTION_TIMEOUT + 1  # slight buffer
            )
        except asyncio.TimeoutError:
            self.logger.log_connection_event(Level.LEVEL_ERROR, Event.EXECUTION_TIMEOUT)
            self.process.kill()
            await self.process.wait()
            return 202

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
                break

        try:
            return int(pid_str)  # Convert the PID string to an integer
        except ValueError:
            print(f"Error: Failed to convert PID '{pid_str}' to an integer.")
            return None

    async def stream_output(self):
        
        # Wait for the process to be ready before starting streaming
        await self.process_ready_event.wait()

        while True:
            chunk = await self.process.stdout.read(1024)
            if not chunk:
                break  # EOF reached

            encoded_line = base64_encode(chunk.decode()).decode('utf-8')
            await self.send(self.server_create_response(protocol.CODE_RUN_SCRIPT, (False, encoded_line)))
            
        await self.process.wait()
        self.container_running = False
        self.process_ready_event.clear()
    
    async def moniter_input_syscalls(self):
        """
        Asynchronously checks if the process is blocked on input from stdin.
        """
        # Wait for the process to be ready before starting streaming
        await self.process_ready_event.wait()

        command = f"docker exec {self.container_name} ps -o state= -p {self.pid}"

        while self.container_running:
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            res = await process.stdout.read()
            if res.decode().strip() == 'S':
                await self.stream_input()
            
    async def stream_input(self):
        """
        Asynchronously streams input to the running container's stdin.
        """
        await self.send(self.server_create_response(protocol.CODE_BLOCKED_INPUT, None))
    
        input = await self.handle_request(await self.recv())

        # Command to write to process's stdin in the container
        command = [
            "docker", "exec", "-i", self.container_name,
            "bash", "-c", f"cat > /proc/{self.pid}/fd/0"
        ]

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


def register_user(email: str, password: str) -> bool:
    regi_success = db.add_user(email, password)

    if regi_success:
        user_id: int = db.get_user_id(email)
        user_storage = user_file_manager.UserStorage(user_id)
        db.set_user_files_struct(email, user_storage)
        return True
    
    return False


def login_user(email: str, password: str) -> str | bool:
    """
    Login succeed: Returns string json of user's files hierarchy 
    \nLogin Failed: Returns False
    """
    try:
        if db.is_password_ok(email, password):
            user_storage: user_file_manager.UserStorage = db.get_user_files_struct(email)
            return str(user_storage)
        return False
    
    except errors.UserNotFoundError as err:
        print(f"Error: {err}")


def user_storage_add(email, new_node: str) -> bool:

    user_storage: user_file_manager.UserStorage = db.get_user_files_struct(email)

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
    
    db.set_user_files_struct(email, user_storage)

    # Storage update succeeded
    return True


def user_file_delete(email, file_path: str) -> bool:

    user_storage: user_file_manager.UserStorage = db.get_user_files_struct(email)

    try:
        user_storage.delete_file(file_path)
    except Exception as e:
        print(f"error: {e}")
        # Storage update failed
        return False

    db.set_user_files_struct(email, user_storage)

    # Storage update succeeded
    return True


def get_user_file(email, path: str) -> str | bool:

    user_id = db.get_user_id(email)

    try:
        file_content = user_file_manager.get_file_content(user_id, path)
        return file_content
    except FileNotFoundError:
        return False


def update_user_file(email, path: str, new_content: str) -> bool:

    user_id = db.get_user_id(email)

    try:
        user_file_manager.update_file_content(user_id, path, new_content)
        return True
    except FileNotFoundError:
        return False
    

def base64_encode(to_encode: str):
    return base64.b64encode(to_encode.encode('utf-8'))

def base64_decode(encoded):
    return base64.b64decode(encoded).decode('utf-8')
