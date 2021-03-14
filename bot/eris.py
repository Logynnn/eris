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

import logging
import traceback
import colorama
import discord
from discord.ext import commands

import config
from utils import http
from utils import cache
from utils import database
from utils import modules
from utils.context import ErisContext


# Quando for remover o Jishaku.
import os
os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'True'


log = logging.getLogger(__name__)


DIM    = colorama.Style.DIM
YELLOW = colorama.Fore.LIGHTYELLOW_EX
RED    = colorama.Fore.LIGHTRED_EX
GREEN  = colorama.Fore.LIGHTGREEN_EX
RESET  = colorama.Style.RESET_ALL


COSMIC_GUILD_ID = 795017809402921041
STAFF_ROLE_ID   = 795026574453899304


class Eris(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=get_prefix, intents=intents)

        loop = self.loop
        run = loop.run_until_complete

        self.is_first_launch = True
        self.default_prefix = '?'

        # Criar sessão HTTP com `aiohttp`.
        log.info('Creating client HTTP session.')
        self.session = run(http.create_session(connector=self.http.connector, loop=loop))

        # Criar conexão com o Redis (cache).
        log.info('Creating connection with Redis.')
        self.cache = run(cache.create_cache(config.redis, loop=loop))

        # Criar conexão com o PostgreSQL (banco de dados).
        log.info('Creating connection with PostgreSQL.')
        self.pool = run(database.create_pool(config.postgres, loop=loop))

        # Carregar as extensões do bot.
        log.info('Loading all initial extensions.')
        for ext in modules.get_all_extensions():
            self.load_extension(ext)

        # Carregar o Jishaku já que ele será útil por enquanto.
        self.load_extension('jishaku')

        # Dispachar um evento para que cada cog
        # faça suas configurações necessárias.
        self.dispatch('bot_load')

    @property
    def cosmic(self) -> discord.Guild:
        return self.get_guild(COSMIC_GUILD_ID)

    @property
    def staff_role(self) -> discord.Role:
        return self.cosmic.get_role(STAFF_ROLE_ID)

    def load_extension(self, name: str):
        try:
            super().load_extension(name)
        except Exception:
            log.exception(f"Extension '{name}' could not be loaded.")

            print(DIM + traceback.format_exc() + RESET, end='')
            print(RED + f"[{name}] Extensão não pôde ser carregada." + RESET)
        else:
            log.info(f"Extension '{name}' has been loaded.")

            print(GREEN + f"[{name}] Extensão carregada com sucesso." + RESET)

    async def process_commands(self, message: discord.Message):
        # Nós sobrescrevemos este método para usar no `Context` personalizado.
        # Também removo umas condições que tinha aqui já que quero migrá-las 
        # para o `on_message`.
        ctx = await self.get_context(message, cls=ErisContext)
        await self.invoke(ctx)

    async def on_ready(self):
        if self.is_first_launch:
            # Isso é necessário já que alguns cogs usam o evento `on_ready`
            # para fazer coisas necessárias, ao mesmo tempo que não quero
            # que esse evento seja disparado diversas vezes.
            self.is_first_launch = False
            self.dispatch('first_launch')

            print(YELLOW + f'[{__name__}] Online com {len(self.users)} usuários.' + RESET)

    async def on_message(self, message: discord.Message):
        # Verifico se o autor da mensagem é uma instância
        # de `Member`. Assim consigo evitar mensagens de
        # webhooks.
        if not isinstance(message.author, discord.Member):
            return

        if message.author.bot:
            return

        # Caso a mensagem passe pelas condições anteriores
        # então eu dispacho um evento para ser usado em
        # cogs que necessitam dessa mensagem "sanitizada".
        self.dispatch('regular_message', message)

        # E então eu processo a mensagem para um comando.
        await self.process_commands(message)

    async def close(self):
        # Antes de fechar o bot, temos que fechar nossa sessão HTTP.
        # Caso contrário, o `aiohttp` irá reclamar que não fechamos
        # a sessão.
        log.info('Closing client HTTP session.')
        await self.session.close()

        await super().close()


async def get_prefix(bot: Eris, message: discord.Message) -> list[str]:
    # Tenta obter um prefixo personalizado no cache.
    # Caso não consiga, usa o prefix padrão `?`.
    # `eris ` é um prefixo global e não pode ser mudado.
    prefix = await bot.cache.get(f'config/user/{message.author.id}/prefix')

    if prefix is None:
        prefix = bot.default_prefix

    return ['eris ', prefix]
