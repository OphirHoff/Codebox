import websockets
import asyncio
import json
import protocol
from db import database
from utils import user_file_manager
import errors
import traceback

# Globals
db = database.Database()
SCRIPT = "script.py"

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
                print(f"Received from client: {msg}")
                response = await self.handle_request(msg)
                if response:
                    await self.websocket.send(response)
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {self.email or 'unknown'}")
        finally:
            self.server.unregister_user(self.websocket)

    def server_create_response(self, request, data):

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
        
        elif request == protocol.CODE_RUN_SCRIPT:
            serialized_data = { 'output' : data }
            to_send = f"{protocol.CODE_OUTPUT}~{json.dumps(serialized_data)}"
        
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

            elif code == protocol.CODE_RUN_SCRIPT:
                await self.run_script(data[0])

            elif code == protocol.CODE_STORAGE_ADD:
                data: dict = json.loads(data[0])
                user_storage_add(self.email, data)
                to_send = None  # To fix - return appropriate response
        
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())

        return to_send


    async def run_script(self, data):

            code = (json.loads(data))['code']
            
            with open('script.py', 'w') as file:
                file.write(code)

            process = await asyncio.create_subprocess_exec(
                'python', '-u', 'script.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            async for line in process.stdout:
                print(line.decode())
                await self.websocket.send(self.server_create_response(protocol.CODE_RUN_SCRIPT, line.decode()))
            
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
