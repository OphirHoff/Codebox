import websockets
import asyncio
import subprocess
import os
import json
import protocol
from db import database
from utils import user_file_manager
import errors
import traceback

# Globals
db = database.Database()
SCRIPT = "script.py"
SANDBOX_WORKDIR = '/home/sandboxuser/app'
EXECUTION_MAX_TIME = 60  # seconds

class Server:
    def __init__(self):
        self.clients: dict = {}  # websocket -> email

    async def handle_client(self, websocket):
        client_ip, client_port = websocket.remote_address
        print(f"\nNew Client connected. ({client_ip}, {client_port})")
        handler = ClientHandler(websocket, self)
        await handler.handle()

    def register_logged_user(self, websocket, email):
        self.clients[websocket] = email

    def unregister_user(self, websocket):
        self.clients.pop(websocket, None)


class ClientHandler:
    def __init__(self, websocket, server):
        self.websocket = websocket
        self.server: Server = server  # reference to the main server (for shared state)
        self.email = None  # will be set after login

    async def handle(self):
        try:
            while True:
                msg = await self.websocket.recv()
                print(f"Received: {msg}")
                response = await self.handle_request(msg)
                if response:
                    await self.websocket.send(response)
                    print(f"Sent: {response}")
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {self.email or 'unknown'}")
        finally:
            self.server.unregister_user(self.websocket)

    def server_create_response(self, request, data, error=None):

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
        
        elif request == protocol.CODE_GET_FILE:
            if data or data == '':  # File exists (data == '' to support empty files)
                serialized_data = { 'content' : data }
                to_send = f"{protocol.CODE_FILE_CONTENT}~{json.dumps(serialized_data)}"
            else:  # File wasn't found
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_FILE_NOT_FOUND}"

        elif request == protocol.CODE_SAVE_FILE:
            if data:
                to_send = protocol.CODE_FILE_SAVED
            else:
                to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_FILE_NOT_FOUND}"

        elif request == protocol.CODE_RUN_SCRIPT or request == protocol.CODE_RUN_FILE:
            
            execution_finished, data = data

            if not execution_finished:
                serialized_data = { 'output' : data }
                to_send = f"{protocol.CODE_OUTPUT}~{json.dumps(serialized_data)}"
            else:
                to_send = f"{protocol.CODE_RUN_END}~{data}"
        
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

            elif code == protocol.CODE_STORAGE_ADD:
                data: dict = json.loads(data[0])
                user_storage_add(self.email, data)
                to_send = None  # To fix - return appropriate response
        
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())

        return to_send


    async def run_script(self, data) -> bool:

        code = (json.loads(data))['code']
        
        command = [
            "docker", "run", "--rm",
            "--cpus=0.5",
            "--memory=128m",
            "--pids-limit=64",
            "--network", "none",
            "python_runner",
            "/bin/bash", "-c",
            f"touch script.py && echo '{code}' > script.py && python3 -u script.py"
            
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        await self.stream_output(process)

        return process.returncode

    async def run_from_storage(self, path: str) -> bool:
        
        user_id = db.get_user_id(self.email)
        user_path = user_file_manager.user_folder_name(user_id)
        
        command = [
            "docker", "run", "--rm",
            "--cpus=0.5",
            "--memory=128m",
            "--pids-limit=64",
            "--network", "none",
            "-v", f"{os.path.abspath(user_path)}:{SANDBOX_WORKDIR}:ro",
            "python_runner",
            "python3", "-u", path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        await self.stream_output(process)

        return process.returncode
    
    async def stream_output(self, process):

        async for line in process.stdout:
                await self.websocket.send(self.server_create_response(protocol.CODE_RUN_SCRIPT, (False, line.decode())))
            
        await process.wait()


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


def user_storage_add(email, new_node: str):

    user_storage: user_file_manager.UserStorage = db.get_user_files_struct(email)

    create_type: str = new_node[protocol.JsonEntries.NODE_TYPE]
    path: str = new_node[protocol.JsonEntries.NODE_PATH]

    if create_type == user_file_manager.FileType.FILE.value:
        user_storage.create_file(path)
    elif create_type == user_file_manager.FileType.FOLDER.value:
        user_storage.create_dir(path)
    else:
        raise errors.InvalidEntry(protocol.JsonEntries.NODE_TYPE, create_type)
    
    db.set_user_files_struct(email, user_storage)


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

