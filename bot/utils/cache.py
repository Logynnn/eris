'''
MIT License

Copyright (c) 2021 Caio Alexandre

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
'''
This Source Code Form is subject to the
terms of the Mozilla Public License, v.
2.0. If a copy of the MPL was not
distributed with this file, You can
obtain one at
http://mozilla.org/MPL/2.0/.
'''

from asyncio import AbstractEventLoop

from aioredis import Redis, create_redis_pool


async def create_cache(address: str, *, loop: AbstractEventLoop) -> Redis:
    '''Sessão do Redis para cache.

    Parameters
    ----------
    address: :class:`str`
        O endereço do servidor Redis.
    loop: :class:`AbstractEventLoop`
        O loop assíncrono de eventos.

    Returns
    -------
    :class:`Redis`
        Uma instância de uma sessão do Redis.
    '''
    pool = await create_redis_pool(address=address, loop=loop, encoding='utf-8')
    # Antes de retornar a pool, quero remover tudo do cache
    # para manter as coisas mais limpas e organizadas.
    await pool.flushall()
    return pool
