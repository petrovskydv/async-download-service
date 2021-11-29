import asyncio


async def archive():
    proc = await asyncio.create_subprocess_exec(
        "zip", "-r", "-", "test_photos",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    with open('archive.zip', 'w+b') as f:
        while not proc.stdout.at_eof():
            print('прочитали порцию')
            data = await proc.stdout.read(512 * 1024)
            f.write(data)


asyncio.run(archive())
