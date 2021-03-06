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

        # Criar sess??o HTTP com `aiohttp`.
        log.info('Creating client HTTP session.')
        self.session = run(http.create_session(connector=self.http.connector, loop=loop))

        # Criar conex??o com o Redis (cache).
        log.info('Creating connection with Redis.')
        self.cache = run(cache.create_cache(config.redis, loop=loop))

        # Criar conex??o com o PostgreSQL (banco de dados).
        log.info('Creating connection with PostgreSQL.')
        self.pool = run(database.create_pool(config.postgres, loop=loop))

        # Carregar as extens??es do bot.
        log.info('Loading all initial extensions.')
        for ext in modules.get_all_extensions():
            self.load_extension(ext)

        # Carregar o Jishaku j?? que ele ser?? ??til por enquanto.
        self.load_extension('jishaku')

        # Dispachar um evento para que cada cog
        # fa??a suas configura????es necess??rias.
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
            print(RED + f"[{name}] Extens??o n??o p??de ser carregada." + RESET)
        else:
            log.info(f"Extension '{name}' has been loaded.")

            print(GREEN + f"[{name}] Extens??o carregada com sucesso." + RESET)

    async def process_commands(self, message: discord.Message):
        # N??s sobrescrevemos este m??todo para usar no `Context` personalizado.
        # Tamb??m removo umas condi????es que tinha aqui j?? que quero migr??-las 
        # para o `on_message`.
        ctx = await self.get_context(message, cls=ErisContext)
        await self.invoke(ctx)

    async def on_ready(self):
        if self.is_first_launch:
            # Isso ?? necess??rio j?? que alguns cogs usam o evento `on_ready`
            # para fazer coisas necess??rias, ao mesmo tempo que n??o quero
            # que esse evento seja disparado diversas vezes.
            self.is_first_launch = False
            self.dispatch('first_launch')

            print(YELLOW + f'[{__name__}] Online com {len(self.users)} usu??rios.' + RESET)

    async def on_message(self, message: discord.Message):
        # S?? quero que o bot responda quando ele estiver pronto,
        # j?? que os comandos precisam do cache atualizado.
        if not self.is_ready():
            return

        # Verifico se o autor da mensagem ?? uma inst??ncia
        # de `Member`. Assim consigo evitar mensagens de
        # webhooks.
        if not isinstance(message.author, discord.Member):
            return

        if message.author.bot:
            return

        # Caso a mensagem passe pelas condi????es anteriores
        # ent??o eu dispacho um evento para ser usado em
        # cogs que necessitam dessa mensagem "sanitizada".
        self.dispatch('regular_message', message)

        # E ent??o eu processo a mensagem para um comando.
        await self.process_commands(message)

    async def close(self):
        # Antes de fechar o bot, temos que fechar nossa sess??o HTTP.
        # Caso contr??rio, o `aiohttp` ir?? reclamar que n??o fechamos
        # a sess??o.
        log.info('Closing client HTTP session.')
        await self.session.close()

        await super().close()


async def get_prefix(bot: Eris, message: discord.Message) -> list[str]:
    # Tenta obter um prefixo personalizado no cache.
    # Caso n??o consiga, usa o prefix padr??o `?`.
    # `eris ` ?? um prefixo global e n??o pode ser mudado.
    prefix = await bot.cache.get(f'config/user/{message.author.id}/prefix')

    if prefix is None:
        prefix = bot.default_prefix

    return ['eris ', prefix]
