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

import discord
import humanize
from discord.ext import commands


class Logger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_first_ready(self):
        self.cosmic = self.bot.cosmic
        self.logger_channel = self.bot.logger_channel

        self.colour = self.cosmic.me.colour

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        author = message.author
        channel = message.channel

        if author == self.cosmic.me:
            return

        info = [
            f'**ID:** `{message.id}`',
            f'**Canal:** {channel.mention} (`{channel.id}`)'
        ]

        embed = discord.Embed(title='Mensagem deletada', colour=self.colour)
        embed.description = f'**Mensagem:**\n```\n{message.clean_content or "<Não há conteúdo>"}```'

        embed.set_author(name=f'{author} ({author.id})', icon_url=author.avatar_url)
        embed.set_thumbnail(url=author.avatar_url)
        embed.add_field(name='Informações', value='\n'.join(info))

        await self.logger_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        author = after.author
        channel = after.channel

        if author == self.cosmic.me:
            return

        info = [
            f'**ID:** `{after.id}`',
            f'**Canal:** {channel.mention} (`{channel.id}`)'
        ]

        contents = [
            f'**Antes:**\n```\n{before.clean_content or "<Não há conteúdo>"}```',
            f'**Depois:**\n```\n{after.clean_content or "<Não há conteúdo>"}```'
        ]

        embed = discord.Embed(title='Mensagem editada', colour=self.colour)
        embed.description = '\n'.join(contents)

        embed.set_author(name=f'{author} ({author.id})', icon_url=author.avatar_url)
        embed.set_thumbnail(url=author.avatar_url)
        embed.add_field(name='Informações', value='\n'.join(info))

        await self.logger_channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Logger(bot))
