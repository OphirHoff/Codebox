import asyncio
import keyboard
import websockets
from controllers import websocket_controller

HOST = "0.0.0.0"
PORT = 8765

async def shutdown_signal():
    while True:
        # Use asyncio.to_thread to prevent blocking the event loop
        if await asyncio.to_thread(keyboard.is_pressed, 'q'):
            break
        await asyncio.sleep(0.1)  # Yield control back to event loop

async def main():

    print("Starting Server... (press 'q' to stop)\n")

    server = websocket_controller.Server(PORT)
    async with websockets.serve(server.handle_client, HOST, PORT):
        await shutdown_signal()
    
    server.close()
    print("\nServer closed.")
    

if __name__ == "__main__":
    asyncio.run(main())
