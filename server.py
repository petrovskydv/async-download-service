import asyncio
import datetime
import os.path

import aiofiles
from aiohttp import web

INTERVAL_SECS = 1


async def archivate(request):
    response = web.StreamResponse()
    archive_hash = request.match_info.get('archive_hash')
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'
    await response.prepare(request)

    directory_path = os.path.join('test_photos', archive_hash)
    proc = await asyncio.create_subprocess_exec(
        "zip", "-r", "-", directory_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    while not proc.stdout.at_eof():
        data = await proc.stdout.read(512 * 1024)
        await response.write(data)

    return response


async def uptime_handler(request):
    response = web.StreamResponse()

    # Большинство браузеров не отрисовывают частично загруженный контент, только если это не HTML.
    # Поэтому отправляем клиенту именно HTML, указываем это в Content-Type.
    response.headers['Content-Type'] = 'text/html'

    # Отправляет клиенту HTTP заголовки
    await response.prepare(request)

    while True:
        formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f'{formatted_date}<br>'  # <br> — HTML тег переноса строки

        # Отправляет клиенту очередную порцию ответа
        await response.write(message.encode('utf-8'))

        await asyncio.sleep(INTERVAL_SECS)


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        # web.get('/archive/7kna/', uptime_handler),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
