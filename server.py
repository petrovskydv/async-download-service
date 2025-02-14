import argparse
import asyncio
import logging
import os.path
from asyncio import CancelledError

import aiofiles
from aiohttp import web

logger = logging.getLogger('marathon-bot')


async def archivate(request: web.Request):
    app = request.app
    archive_hash = request.match_info['archive_hash']
    directory_path = os.path.join(app['photo_path'], archive_hash)
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
            await asyncio.sleep(app['delay'])
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

    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    app['delay'] = args.delay
    app['photo_path'] = args.path
    web.run_app(app)


if __name__ == '__main__':
    main()
