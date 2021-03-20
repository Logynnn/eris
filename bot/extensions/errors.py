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

import datetime
import traceback
import re

import humanize
import discord
from discord.ext import commands
from discord.ext.commands.errors import *
from asyncpg import Record

from eris import Eris
from utils import database
from utils import checks
from utils.menus import ErisMenuPages
from utils.context import ErisContext


ERRORS_CHANNEL_ID = 815319319088857129


class ErrorTracker(database.Table, table_name='error_tracker'):
    id = database.PrimaryKeyColumn()

    created = database.Column(database.Datetime, default="NOW() AT TIME ZONE 'utc'")
    error = database.Column(database.String)
    is_solved = database.Column(database.Boolean, default=False)
    message_id = database.Column(database.Integer(big=True), nullable=True)


class InvalidTicket(commands.BadArgument):
    def __init__(self):
        super().__init__('Invalid ticket ID provided')


class Ticket:
    def __init__(self, *, record: Record):
        self.id = record['id']
        self.error = record['error']
        self.message_id = record['message_id']
        self.is_solved = record['is_solved']
        self.created_at = record['created']

    def __repr__(self):
        return '<Ticket id={0.id} created_at={0.created_at!r} is_solved={0.is_solved}>'.format(self)

    def __str__(self):
        return self.error


class TicketConverter(commands.Converter):
    async def convert(self, ctx: ErisContext, argument: str):
        try:
            # Remove o "#" caso o usuário use "#1", por exemplo.
            ticket_id = int(argument.lstrip('#'))
        except ValueError:
            raise InvalidTicket()

        sql = '''
            SELECT * FROM error_tracker
            WHERE id = $1;
        '''
        record = await ctx.pool.fetchrow(sql, ticket_id)

        return Ticket(record=record)


class Errors(commands.Cog):
    '''Comandos relacionados ao tratamento de erros.'''

    def __init__(self, bot: Eris):
        self.bot = bot

    @commands.Cog.listener()
    async def on_first_launch(self):
        self.channel = self.bot.cosmic.get_channel(ERRORS_CHANNEL_ID)

    async def _send_confirmation(self, ctx: ErisContext, error: CommandError, ticket_id: int):
        command = f'{ctx.prefix}{self.error_status.qualified_name}'
        messages = [
            'Eita, um erro desconhecido aconteceu:',
            f'```py\n{error}\n```',
            f'**Este erro foi reportado para os desenvolvedores com o ID `#{ticket_id}`**.',
            f'Você pode acompanhar o status do erro usando `{command} {ticket_id}`.'
        ]

        await ctx.reply('\n'.join(messages))

    async def _log_error(self, ctx: Eris, error: CommandError, ticket_id: int) -> discord.Message:
        error_type = type(error)
        error_trace = error.__traceback__

        traceback_list = traceback.format_exception(error_type, error, error_trace)
        lines = []

        for line in traceback_list:
            lines.append(re.sub(r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', line))

        content = discord.utils.escape_markdown(ctx.message.content)

        command_info = [
            f'**Author:** {ctx.author.mention} (`{ctx.author.id}`)',
            f'**Canal:** {ctx.channel.mention} (`{ctx.channel.id}`)',
            f'**Comando:** ```{content}```'
        ]

        embed = discord.Embed(colour=0x2f3136)
        embed.title = f'[#{ticket_id}] Um erro desconhecido aconteceu'
        embed.description = f'```py\n{"".join(lines)[:2000]}\n```'

        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name='Contexto do comando', value='\n'.join(command_info))

        return await self.channel.send(embed=embed)

    async def create_ticket(self, ctx: ErisContext, error: CommandError):
        '''Cria um ticket de erro.

        Parameters
        ----------
        ctx: :class:`ErisContext`
            O contexto do erro.
        error: :class:`CommandError`
            O erro ocorrido ao invocar o comando.
        '''        
        sql = '''
            INSERT INTO error_tracker (created, error)
            VALUES ($1, $2)
            RETURNING id;
        '''
        record = await ctx.pool.fetchrow(sql, ctx.message.created_at, str(error))
        ticket_id = record[0]

        await self._send_confirmation(ctx, error, ticket_id)
        message = await self._log_error(ctx, error, ticket_id)

        sql = '''
            UPDATE error_tracker
            SET message_id = $2
            WHERE id = $1;
        '''
        await ctx.pool.execute(sql, ticket_id, message.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: ErisContext, error: CommandError):
        # Erros personalizados.
        if isinstance(error, InvalidTicket):
            return await ctx.reply('Não há um ticket de erro com este ID.')

        # Erros do `discord.py`.
        elif isinstance(error, MissingRequiredArgument):
            return await ctx.reply(f'Está faltando o argumento `{error.param.name}`.')

        elif isinstance(error, TooManyArguments):
            return

        elif isinstance(error, MemberNotFound):
            return await ctx.reply(f'Esse não é um membro válido: `{error.argument}`.')

        elif isinstance(error, ChannelNotFound):
            return await ctx.reply(f'Esse não é um canal válido: `{error.argument}`.')

        elif isinstance(error, CommandNotFound):
            if ctx.prefix == '':
                return

            return await ctx.reply(f'O comando `{ctx.invoked_with}` não existe.')

        elif isinstance(error, CheckFailure):
            return await ctx.reply('Você não tem permissão para usar este comando.')

        elif isinstance(error, CommandOnCooldown):
            delta = humanize.precisedelta(error.retry_after, format='%0.0f')
            return await ctx.reply(f'Espere **{delta}** antes de usar este comando novamente.')

        # Caso não passe por nenhum dos erros acima, então
        # criamos um ticket, assim o usuário pode acompanhar
        # o status do erro.
        await self.create_ticket(ctx, error)

    @commands.group(aliases=['exception'])
    async def error(self, ctx: ErisContext):
        '''
        Comandos de tickets de erro.
        '''
        if not ctx.invoked_subcommand:
            await ctx.send_help(self.error)

    @error.command(name='status', alises=['lookup'])
    async def error_status(self, ctx: ErisContext, ticket: TicketConverter):
        '''
        Vê o status de um ticket de erro.
        '''
        delta = humanize.precisedelta(ctx.message.created_at - ticket.created_at, format='%0.0f')
        is_solved = ctx.tick(ticket.is_solved)

        messages = [
            f'**ID:** `#{ticket.id}`',
            f'**Criado há:** {delta}',
            f'**Foi resolvido:** {is_solved}',
            f'**Erro:** ```py\n{ticket.error}\n```'
        ]

        await ctx.reply('\n'.join(messages))

    @error.command(name='solve', aliases=['fix'])
    @checks.is_staffer()
    async def error_solve(self, ctx: ErisContext, ticket: TicketConverter):
        '''
        Define um ticket de erro como resolvido.
        '''
        sql = '''
            UPDATE error_tracker
            SET is_solved = TRUE, message_id = NULL
            WHERE id = $1;
        '''
        await ctx.pool.execute(sql, ticket.id)

        message = self.channel.get_partial_message(ticket.message_id)
        await message.delete()

        await ctx.reply(f'O ticket de erro `#{ticket.id}` foi marcado como resolvido.')

    @error.command(name='list', aliases=['all'], ignore_extra=False)
    async def error_list(self, ctx: ErisContext):
        '''
        Mostra todos os tickets de erros ativos.
        '''
        sql = '''
            SELECT id, created, error FROM error_tracker
            WHERE is_solved = FALSE
        '''
        fetch = await ctx.pool.fetch(sql)

        if not fetch:
            return await ctx.reply('Não há nenhum erro registrado, isso é um bom sinal.')

        entries = []

        for record in fetch:
            error = record['error']
            ticket_id = record['id']
            created_at = record['created']

            delta = humanize.precisedelta(ctx.message.created_at - created_at, format='%0.0f')
            entries.append(f'`[#{ticket_id}]` **Há {delta}**\n```py\n{error}```')

        menu = ErisMenuPages(entries)
        await menu.start(ctx)

    @commands.command()
    async def errors(self, ctx: ErisContext):
        '''
        Mostra todos os tickets de erros ativos.
        '''
        await self.error_list(ctx)


def setup(bot: Eris):
    bot.add_cog(Errors(bot))
