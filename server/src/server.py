import sys
import asyncio
import ssl
import http_server
import websockets
import keyboard
from controllers import websocket_controller

# Server configuration
HOST = "0.0.0.0"  # Bind to all network interfaces
PORT = 8765       # WebSocket server port
HTTP_PORT = 443   # HTTPS server port

# TLS for both WebSocket and HTTP (same certs)
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile="secrets/certs/cert.pem", keyfile="secrets/certs/key.pem")

async def shutdown_signal():
    """
    Monitors for Ctrl+Q keypress to initiate server shutdown.
    Returns when shutdown signal is detected.
    """
    while True:
        # Use asyncio.to_thread to prevent blocking the event loop
        if await asyncio.to_thread(keyboard.is_pressed, 'ctrl+q'):
            break
        await asyncio.sleep(0.1)  # Yield control back to event loop 


async def main(db_server_ip: str):
    """
    Initializes and runs the server with both HTTP and WebSocket endpoints.
    
    Args:
        db_server_ip: IP address of the database server
    """
    print("Starting Server... (press 'q' to stop)\n")

    await http_server.start_http_server(HOST, HTTP_PORT, ssl_context)

    server = websocket_controller.Server(db_server_ip)
    await server.initialize_db_connections()
    
    async with websockets.serve(server.handle_client, HOST, PORT, ssl=ssl_context):
        await shutdown_signal()
    
    await server.close()
    print("\nServer closed.")
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Correct args usage: py server.py <DB server IP addr.>")
    else:
        asyncio.run(main(sys.argv[1]))
