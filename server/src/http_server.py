"""
HTTPS server implementation for serving the web editor interface.

This module provides a secure HTTPS server using aiohttp that serves:
- A web-based editor interface at the root path
- Static files from the editor directory
"""
import os
from aiohttp import web

async def start_http_server(host_ip: str, port: int, ssl_context) -> None:
    """
    Initialize and start the HTTPS server.

    Args:
        host_ip: IP address to bind the server to
        port: Port number to listen on
        ssl_context: SSL context for HTTPS encryption

    The server serves the editor's index.html at root path and
    static files from the editor directory.
    """
    app = web.Application()

    # Serve index.html when root is visited
    async def index_handler(request):
        """Serve the editor's index.html page for root path requests."""
        return web.FileResponse(os.path.join('../../editor', 'index.html'))

    app.router.add_get('/', index_handler)

    # Serve static files
    app.router.add_static('/', path='../../editor', show_index=False)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host_ip, port=port, ssl_context=ssl_context)
    await site.start()

    print(f"HTTPS server running at https://{host_ip}:{port}\n")