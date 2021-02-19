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

import discord
from discord.ext import commands

from utils.context import Context


# TODO: Adicionar uma documentação decente.

COSMIC_GUILD_ID = 795017809402921041
STAFF_ROLE_ID = 795026574453899304
GENERAL_CHANNEL_ID = 810910658458550303

all_extensions = []
for root, _, files in os.walk('extensions'):
    for file in files:
        path = os.path.join(root, file)

        if not os.path.isfile(path):
            continue

        path, ext = os.path.splitext(path)
        if ext != '.py':
            continue

        # regex é um ser muito estranho.
        extension = re.sub(r'\\|\/', '.', path)
        all_extensions.append(extension)


class Bellatrix(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='b/', intents=discord.Intents.all())
        self.logger = logging.getLogger('bellatrix')

    @property
    def cosmic(self) -> discord.Guild:
        return self.get_guild(COSMIC_GUILD_ID)

    async def on_ready(self):
        self.staff_role = self.cosmic.get_role(STAFF_ROLE_ID)
        self.general_channel = self.cosmic.get_channel(GENERAL_CHANNEL_ID)

        self._image_url_regex = re.compile(
            r'''http[s]?://
            (?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))
            +\.(?:jpg|jpeg|png|gif|webp)$''',
            re.VERBOSE)
        self._emoji_regex = re.compile(r'<:(\w+):(\d+)>')

        self.load_extension('jishaku')

        for ext in all_extensions:
            try:
                self.load_extension(ext)
            except Exception:
                self.logger.exception(
                    f'Extension \'{ext}\' could not be loaded.')
            else:
                self.logger.info(f'Extension \'{ext}\' has been loaded.')

        print(f'Online com {len(self.users)} usuários')

    async def on_message(self, message: discord.Message):
        if not isinstance(message.author, discord.Member):
            return

        if message.author.bot:
            return

        self.dispatch('regular_message', message)
        await self.process_commands(message)

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)
