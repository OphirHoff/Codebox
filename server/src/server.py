import asyncio
import websockets
import protocol
import db.database as database
import traceback
import errors

# Globals
db = database.Database()


def register_user(email: str, password: str):
    return db.add_user(email, password)

def login_user(email: str, password: str):
    try:
        return db.is_password_ok(email, password)
    except errors.UserNotFoundError as err:
        print(f"Error: {err}")

def server_create_response(request, data):

    if request == protocol.CODE_REGISTER:
        if data:
            # Registration succeeded
            to_send = protocol.CODE_REGISTER_SUCCESS
        else:
            # Registration failed (taken email address)
            to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_USER_EXIST}"
    
    elif request == protocol.CODE_LOGIN:
        if data:
            # Login succeeded
            to_send = protocol.CODE_LOGIN_SUCCESS
        else:
            to_send = f"{protocol.CODE_ERROR}~{protocol.ERROR_LOGIN_FAILED}"
    
    return to_send


def server_handle_request(request: str):
    
    request_fields = request.split('~')
    request_code: str = request_fields[0]
    request_data: list = request_fields[1:]

    to_send = ''

    try:
        if request_code == protocol.CODE_REGISTER:
            email, password = request_data
            res = register_user(email, password)
            to_send = server_create_response(request_code, res)
        
        elif request_code == protocol.CODE_LOGIN:
            email, password = request_data
            res = login_user(email, password)
            to_send = server_create_response(request_code, res)
    
    except Exception as e:
        print(f"Error: {e}")

    return to_send
                

async def handle_client(websocket):

    client_ip, client_port, _, _ = websocket.remote_address
    print(f"\nNew Client connected. ({client_ip}, {client_port})")
    
    while True:
        msg = await websocket.recv()
        print(f"server Recieved: {msg}")
        
        response = server_handle_request(msg)

        # data = json.loads(msg)
        # print(data, type(data))
        # with open("script.py", 'w') as file:
        #     file.write(data['code'])
        # run_output = subprocess.run(['python', 'script.py'], capture_output=True, text=True).stdout
        # print('output:', run_output)
        # response = json.dumps({'output': run_output})

        if response != '':
            await websocket.send(response)
            print(f"Server Sent: {response}")


async def main():
    async with websockets.serve(handle_client, "localhost", 8765):
        print("Server up and running.")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())