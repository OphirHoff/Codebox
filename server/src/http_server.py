import os
from aiohttp import web

async def start_http_server(host_ip, port, ssl_context):
    app = web.Application()

    # Serve index.html when root is visited
    async def index_handler(request):
        return web.FileResponse(os.path.join('../../editor', 'index.html'))

    app.router.add_get('/', index_handler)

    # Serve static files
    app.router.add_static('/', path='../../editor', show_index=False)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host_ip, port=port, ssl_context=ssl_context)
    await site.start()

    print(f"HTTPS server running at https://{host_ip}:{port}\n")