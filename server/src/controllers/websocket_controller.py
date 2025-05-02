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
            print(user_storage.files)
            return str(user_storage)
        return False
    
    except errors.UserNotFoundError as err:
        print(f"Error: {err}")


class Server:

    def __init__(self, ip="localhost", port=8765):
        self.ip = ip
        self.port = port
        self.websocket = None

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

    async def server_handle_request(self, request: str):
        
        request_fields = request.split('~')
        request_code: str = request_fields[0]
        request_data: list = request_fields[1:]

        to_send = ''

        try:
            if request_code == protocol.CODE_REGISTER:
                email, password = request_data
                res = register_user(email, password)
                to_send = self.server_create_response(request_code, res)
            
            elif request_code == protocol.CODE_LOGIN:
                email, password = request_data
                res = login_user(email, password)
                to_send = self.server_create_response(request_code, res)

            elif request_code == protocol.CODE_RUN_SCRIPT:
                await self.run_script(request_data[0])
        
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())

        return to_send
                    
    async def handle_client(self, websocket):

        self.websocket = websocket

        client_ip, client_port = self.websocket.remote_address
        print(f"\nNew Client connected. ({client_ip}, {client_port})")
        
        while True:
            msg = await self.websocket.recv()
            print(f"server Recieved: {msg}")
            
            response = await self.server_handle_request(msg)
            print("response:", response)
            if response:
                await self.websocket.send(response)
                print(f"Server Sent: {response}")