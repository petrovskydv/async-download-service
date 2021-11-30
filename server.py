import argparse
import asyncio
import datetime
import logging
import os.path
from asyncio import CancelledError

import aiofiles
from aiohttp import web

INTERVAL_SECS = 1
DELAY = 0
PHOTO_PATH = ''

logger = logging.getLogger('marathon-bot')


async def archivate(request):
    archive_hash = request.match_info.get('archive_hash')
    directory_path = os.path.join(PHOTO_PATH, archive_hash)
    if not os.path.exists(directory_path):
        raise web.HTTPNotFound(reason='Архив не существует или был удален')

    response = web.StreamResponse()
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'
    await response.prepare(request)
    zip_process = await asyncio.create_subprocess_exec(
        "zip", "-r", "-", directory_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while not zip_process.stdout.at_eof():
            data = await zip_process.stdout.read(512 * 1024)
            logger.debug('Sending archive chunk ...')
            await response.write(data)
            await asyncio.sleep(DELAY)
    except (CancelledError, BaseException):
        logger.debug('Download was interrupted')
        raise
    finally:
        try:
            zip_process.kill()
            await zip_process.communicate()
            logger.debug('zip_process was killed')
        except ProcessLookupError:
            logger.debug('zip_process not find')

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


def main():
    parser = argparse.ArgumentParser(
        description='Service for download archives'
    )
    parser.add_argument('-l', '--loglevel', default=os.getenv('LOGGING_LEVEL', 'ERROR'),
                        help='logging level')
    parser.add_argument('-d', '--delay', type=int, default=os.getenv('RESPONSE_DELAY', 0),
                        help='response delay for chunks of zip archive')
    parser.add_argument('-p', '--path', default=os.getenv('FILE_STORAGE_PATH', 'test_photos'),
                        help='path to catalog with photos')

    global DELAY, PHOTO_PATH
    args = parser.parse_args()
    DELAY = args.delay
    PHOTO_PATH = args.path

    logging.basicConfig(
        level=args.loglevel,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)


if __name__ == '__main__':
    main()
