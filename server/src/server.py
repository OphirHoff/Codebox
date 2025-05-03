import asyncio
import websockets
from controllers import websocket_controller

async def main():

    server = websocket_controller.Server()
    async with websockets.serve(server.handle_client, "0.0.0.0", 8765):
        print("Server up and running.")
        await asyncio.Future()  # run forever
    

if __name__ == "__main__":
    asyncio.run(main())
