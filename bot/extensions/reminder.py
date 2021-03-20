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

import asyncio
import typing
import datetime

import discord
import asyncpg
import humanize
from discord.ext import commands

from eris import Eris
from utils import database
from utils.context import ErisContext
from utils.time import UserFriendlyTime
from utils.menus import ErisMenuPages, SourceType


class Reminders(database.Table):
    id = database.PrimaryKeyColumn()

    expires = database.Column(database.Datetime, index=True)
    created = database.Column(database.Datetime, default="NOW() AT TIME ZONE 'utc'")
    event = database.Column(database.String)
    extra = database.Column(database.Json, default="'{}'::jsonb")


class Timer:
    __slots__ = ('args', 'kwargs', 'event', 'id', 'created_at', 'expires')

    def __init__(self, *, record: asyncpg.Record):
        self.id = record['id']

        extra = record['extra']
        self.args = extra.get('args', [])
        self.kwargs = extra.get('kwargs', {})

        self.event = record['event']
        self.created_at = record['created']
        self.expires = record['expires']

    @classmethod
    def temporary(cls, *, expires, created, event, args, kwargs):
        pseudo = {
            'id': None,
            'extra': {'args': args, 'kwargs': kwargs},
            'event': event,
            'created': created,
            'expires': expires
        }

        return cls(record=pseudo)

    def __eq__(self, other: typing.Any):
        return isinstance(other, type(self)) and other.id == self.id

    def __repr__(self):
        return f'<Timer created={self.created_at} expires={self.expires} event={self.event!r}>'

    @property
    def delta(self) -> str:
        return humanize.precisedelta(self.created_at - self.expires, format='%0.0f')


class Reminder(commands.Cog, name='Lembretes'):
    '''Comandos relacionados e lembretes e timers.'''

    def __init__(self, bot: Eris):
        self.bot = bot

        self._have_data = asyncio.Event(loop=bot.loop)
        self._current_timer = None
        self._task = bot.loop.create_task(self.dispatch_timers())

    def cog_unload(self):
        self._task.cancel()

    async def dispatch_timers(self):
        try:
            while not self.bot.is_closed():
                timer = self._current_timer = await self.wait_for_active_timers(days=40)

                await discord.utils.sleep_until(timer.expires)
                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def call_timer(self, timer: Timer):
        sql = 'DELETE FROM reminders WHERE id = $1;'
        await self.bot.pool.execute(sql, timer.id)

        self.bot.dispatch(f'{timer.event}_complete', timer)

    async def wait_for_active_timers(self, *, days: int = 7):
        timer = await self.get_active_timer(days=days)

        if timer:
            self._have_data.set()
            return timer

        self._have_data.clear()
        self._current_timer = None

        await self._have_data.wait()
        return await self.get_active_timer(days=days)

    async def get_active_timer(self, *, days: int = 7) -> Timer:
        sql = '''
            SELECT * FROM reminders
            WHERE expires < (CURRENT_DATE + $1::interval)
            ORDER BY expires
            LIMIT 1;
        '''
        record = await self.bot.pool.fetchrow(sql, datetime.timedelta(days=days))

        return Timer(record=record) if record else None
        
    async def short_timer_optimisation(self, seconds: int, timer: Timer):
        await asyncio.sleep(seconds)
        self.bot.dispatch(f'{timer.event}_complete', timer)

    async def create_timer(self, *args, **kwargs) -> Timer:
        '''Cria um timer.

        Parameters
        ----------
        when: :class:`datetime.datetime`
            Quando o timer deve ativar.
        event: :class:`str`
            O nome do evento para ativar.
            Vai ser transformado em um evento `on_{event}_complete`
        \*args
            Os argumentos para passar no evento.
        \*\*kwargs
            As keywords para passar no evento.
        created: :class:`datetime.datetime`
            Uma keyword especial que diz o tempo da criação do timer.
            Deve fazer os timedeltas mais consistentes.

        Note
        ------
        Os argumentos e as keywords devem ser objetos JSON válidos.

        Returns
        -------
        :class:`Timer`
            O timer a ser usado.
        '''        
        when, event, *args = args
        now = kwargs.pop('created', datetime.datetime.utcnow())

        when = when.replace(microsecond=0)
        now = now.replace(microsecond=0)

        timer = Timer.temporary(expires=when, created=now, event=event, args=args, kwargs=kwargs)
        
        delta = (when - now).total_seconds()
        if delta <= 60:
            self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
            return timer
            
        sql = '''
            INSERT INTO reminders (event, extra, expires, created)
            VALUES ($1, $2::jsonb, $3, $4)
            RETURNING id;
        '''
        record = await self.bot.pool.fetchrow(sql, event, {'args': args, 'kwargs': kwargs}, when, now)
        timer.id = record[0]

        if delta <= (86400 * 40):
            self._have_data.set()

        if self._current_timer and when < self._current_timer.expires:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        return timer

    @commands.group(invoke_without_command=True, aliases=['timer', 'remind'])
    async def reminder(self, ctx: ErisContext, *, when: UserFriendlyTime(commands.clean_content, default='...')):
        '''
        Te lembra de alguma coisa depois de uma certa quantida de tempo.
        '''
        args = (ctx.author.id, ctx.channel.id, when.arg)
        kwargs = {'created': ctx.message.created_at, 'message_id': ctx.message.id}

        timer = await self.create_timer(when.datetime, 'reminder', *args, **kwargs)
        await ctx.reply(f'Certo, em {timer.delta}: **{when.arg}**.')

    @reminder.command(name='list', ignore_extra=False)
    async def reminder_list(self, ctx: ErisContext):
        '''
        Mostra seus timers ativos.
        '''
        sql = '''
            SELECT id, expires, extra #>> '{args,2}' FROM reminders
            WHERE event = 'reminder'
            AND extra #>> '{args,0}'= $1
            ORDER BY expires
            LIMIT 10;
         '''
        fetch = await ctx.pool.fetch(sql, str(ctx.author.id))

        if len(fetch) == 0:
            return await ctx.reply('Você não possui nenhum lembrete ativo.')

        fields = []

        for reminder_id, expires, message in fetch:
            now = datetime.datetime.utcnow()
            delta = humanize.precisedelta(expires - now.replace(microsecond=0), format='%0.0f')

            field = {'name': f'[{reminder_id}] Em {delta}', 'value': message, 'inline': False}
            fields.append(field)

        menu = ErisMenuPages(fields, source=SourceType.FIELD)
        await menu.start(ctx, wait=True)

    @commands.Cog.listener()
    async def on_reminder_complete(self, timer: Timer):
        # Só quero que os timers respondam caso o bot esteja pronto.
        await self.bot.wait_until_ready()

        author_id, channel_id, content = timer.args

        author = self.bot.cosmic.get_member(author_id)
        channel = self.bot.cosmic.get_channel(channel_id)

        if not channel:
            return

        # Uma maneira hardcoded de obter o link da mensagem.
        message_id = timer.kwargs.get('message_id')
        message_url = f'https://discord.com/channels/{self.bot.cosmic.id}/{channel.id}/{message_id}'

        messages = [
            f'Há {timer.delta}: **{content}**.',
            f'**Clique [aqui]({message_url}) para ver a mensagem.**'
        ]

        embed = discord.Embed(description='\n\n'.join(messages), colour=0x2f3136)
        embed.set_author(name=author.display_name, icon_url=author.avatar_url)

        await channel.send(author.mention, embed=embed)


def setup(bot: Eris):
    bot.add_cog(Reminder(bot))
