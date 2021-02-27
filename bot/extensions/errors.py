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

import traceback
import re
from textwrap import dedent

import humanize
import discord
from discord.ext import commands
from discord.ext.commands.errors import *


class Errors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.errors_channel = self.bot.errors_channel
    
    async def log_error(self, ctx: commands.Context, error: commands.CommandError):
        error_type = type(error)
        error_trace = error.__traceback__

        traceback_list = traceback.format_exception(error_type, error, error_trace)
        lines = []

        for line in traceback_list:
            sanitized_line = re.sub(r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', line)
            lines.append(sanitized_line)

        embed = discord.Embed(color=ctx.bot.color)
        embed.title = 'Um erro desconhecido aconteceu'
        embed.description = f'```py\n{"".join(lines)}```'

        content = discord.utils.escape_mentions(ctx.message.content)

        info = dedent(f'''
            Autor: {ctx.author.mention}
            Comando: `{content}`
            Canal: {ctx.channel.mention}
            Mensagem: clique [aqui]({ctx.message.jump_url}).
        ''')

        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.add_field(name='Informações', value=info)

        await self.errors_channel.send(embed=embed)

    async def confirm_error(self, ctx: commands.Context, error: commands.CommandError):
        message = dedent(f'''
            Eita, um erro desconhecido aconteceu:
            ```py\n{error}```
            **Este erro foi reportado para os desenvolvedores.**
        ''')
        await ctx.reply(message)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: CommandError):
        if isinstance(error, CommandOnCooldown):
            delta = humanize.precisedelta(error.retry_after, format='%0.0f')
            return await ctx.reply(f'Espere **{delta}** antes de usar este comando novamente.')

        await self.log_error(ctx, error)
        await self.confirm_error(ctx, error)


def setup(bot: commands.Bot):
    bot.add_cog(Errors(bot))