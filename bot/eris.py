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

import os
import re
import logging
import importlib
from typing import List

import discord
from discord.ext import commands

import config
from utils.context import Context
from utils.modules import get_all_extensions
from utils.cache import create_cache


os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'True'

log = logging.getLogger(__name__)


# TODO: Adicionar uma documentação decente.

class Eris(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.prefix, intents=discord.Intents.all())
        
        self._first_start = True
        run = self.loop.run_until_complete

        self.cache = run(create_cache(config.redis, loop=self.loop))

        log.info('Starting to load initial extensions.')
        for name in get_all_extensions():
            self.load_extension(name)

        # carregar jishaku separadamente.
        self.load_extension('jishaku')

    @property
    def constants(self):
        return importlib.import_module('utils.constants')

    @property
    def cosmic(self) -> discord.Guild:
        return self.get_guild(self.constants.COSMIC_GUILD_ID)

    @property
    def staff_role(self) -> discord.Role:
        return self.cosmic.get_role(self.constants.STAFF_ROLE_ID)

    @property
    def administrator_role(self) -> discord.Role:
        return self.cosmic.get_role(self.constants.ADMINISTRATOR_ROLE_ID)

    @property
    def nitro_booster_role(self) -> discord.Role:
        return self.cosmic.get_role(self.constants.NITRO_BOOSTER_ROLE_ID)

    @property
    def premium_roles(self) -> List[discord.Role]:
        PREMIUM_ROLES = self.constants.PREMIUM_ROLES
        return [self.cosmic.get_role(role_id) for role_id in PREMIUM_ROLES]

    @property
    def mute_role(self) -> discord.Role:
        return self.cosmic.get_role(self.constants.MUTE_ROLE_ID)

    @property
    def notifications_role(self) -> discord.Role:
        return self.cosmic.get_role(self.constants.NOTIFICATIONS_ROLE_ID)

    @property
    def log_channel(self) -> discord.TextChannel:
        return self.cosmic.get_channel(self.constants.LOG_CHANNEL_ID)

    @property
    def general_channel(self) -> discord.TextChannel:
        return self.cosmic.get_channel(self.constants.GENERAL_CHANNEL_ID)

    @property
    def errors_channel(self) -> discord.TextChannel:
        return self.cosmic.get_channel(self.constants.ERRORS_CHANNEL_ID)

    @property
    def logger_channel(self) -> discord.TextChannel:
        return self.cosmic.get_channel(self.constants.LOGGER_CHANNEL_ID)

    @property
    def color(self) -> discord.Color:
        return self.cosmic.me.color

    async def on_ready(self):
        if self._first_start:
            self._first_start = False
            self.dispatch('first_ready')

        print(f'Online com {len(self.users)} usuários')

    async def on_first_ready(self):
        self._image_url_regex = re.compile(
            r'''http[s]?://
            (?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))
            +\.(?:jpg|jpeg|png|gif|webp)$''',
            re.VERBOSE)
        self._emoji_regex = re.compile(r'<:(\w+):(\d+)>')
        self._invite_regex = re.compile(r'(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?', re.VERBOSE)

        log.info(f'{self.__class__.__name__} is ready to go.')

    async def on_message(self, message: discord.Message):
        # não quero ver mensagens enquanto o bot não estiver pronto.
        if not self.is_ready():
            return

        if not isinstance(message.author, discord.Member):
            return

        if message.author.bot:
            return

        if message.guild != self.cosmic:
            return

        self.dispatch('regular_message', message)
        await self.process_commands(message)

    def load_extension(self, name: str):
        try:
            super().load_extension(name)
        except Exception:
            log.exception(f"Extension '{name}' could not be loaded.")
        else:
            log.info(f"Extension '{name}' has been loaded.")

    def unload_extension(self, name: str):
        try:
            super().unload_extension(name)
        except Exception:
            log.exception(f"Extension '{name}' could not be unloaded.")
        else:
            log.info(f"Extension '{name}' has been unloaded.")

    def reload_extension(self, name: str):
        try:
            super().reload_extension(name)
        except Exception:
            log.exception(f"Extension '{name}' could not be reloaded.")
        else:
            log.info(f"Extension '{name}' has been reloaded.")

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    def run(self, *args, **kwargs):
        log.info(f'Trying to run {self.__class__.__name__}.')
        super().run(*args, **kwargs)
