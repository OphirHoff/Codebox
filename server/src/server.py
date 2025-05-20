import asyncio
import ssl
import http_server
import websockets
import keyboard
from controllers import websocket_controller

HOST = "0.0.0.0"
PORT = 8765
HTTP_PORT = 8080

# TLS for both WebSocket and HTTP (same certs)
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile="certs/cert.pem", keyfile="certs/key.pem")

async def shutdown_signal():
    while True:
        # Use asyncio.to_thread to prevent blocking the event loop
        if await asyncio.to_thread(keyboard.is_pressed, 'ctrl+q'):
            break
        await asyncio.sleep(0.1)  # Yield control back to event loop 


async def main():

    print("Starting Server... (press 'q' to stop)\n")

    await http_server.start_http_server(HOST, HTTP_PORT, ssl_context)

    server = websocket_controller.Server()
    async with websockets.serve(server.handle_client, HOST, PORT, ssl=ssl_context):
        await shutdown_signal()
    
    server.close()
    print("\nServer closed.")
    

if __name__ == "__main__":
    asyncio.run(main())
