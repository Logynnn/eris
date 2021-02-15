import datetime
import typing
import asyncio

import asyncpg
import discord
import humanize
from discord.ext import commands

from utils import database


class Reminders(database.Table):
    id = database.PrimaryKeyColumn()

    expires = database.Column(database.Datetime, index=True)
    created = database.Column(database.Datetime, default='now() at time zone \'utc\'')
    event = database.Column(database.String)
    extra = database.Column(database.JSON, default='\'{}\'::jsonb')

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

    @property
    def human_time(self) -> str:
        return humanize.precisedelta(self.expires - self.created_at, format='%0.0f')

    def __eq__(self, other: typing.Any):
        return isinstance(other, type(self)) and other.id == self.id

    def __repr__(self):
        return f'<Timer created={self.created_at} expires={self.expires} event={self.event!r}>'

class Reminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
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
        query = 'DELETE FROM reminders WHERE id = $1'
        await self.bot.manager.execute(query, timer.id)

        self.bot.dispatch(f'{timer.event}_complete', timer)

    async def wait_for_active_timers(self, *, days: int=7):
        timer = await self.get_active_timer(days=days)
        if timer is not None:
            self._have_data.set()
            return timer

        self._have_data.clear()
        self._current_timer = None

        await self._have_data.wait()
        return await self.get_active_timer(days=days)

    async def get_active_timer(self, *, days: int=7) -> Timer:
        query = 'SELECT * FROM reminders WHERE expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1'
        record = await self.bot.manager.fetch_row(query, datetime.timedelta(days=days))
        return Timer(record=record) if record else None 

    async def short_timer_optimisation(self, seconds: int, timer: Timer):
        await asyncio.sleep(seconds)
        self.bot.dispatch(f'{timer.event}_complete', timer)

    async def create_timer(self, *args, **kwargs):
        when, event, *args = args
        now = kwargs.pop('created', datetime.datetime.utcnow())

        timer = Timer.temporary(event=event, args=args, kwargs=kwargs, expires=when, created=now)
        delta = (when - now).total_seconds()
        if delta <= 60:
            self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
            return timer

        query = '''
            INSERT INTO reminders (event, extra, expires, created)
            VALUES ($1, $2::jsonb, $3, $4)
            RETURNING id
        '''

        fetch = await self.bot.manager.fetch_row(query, event, {'args': args, 'kwargs': kwargs}, when, now)
        timer.id = fetch[0]

        if delta <= (86400 * 40):
            self._have_data.set()

        if self._current_timer and when < self._current_timer.expires:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        return timer

def setup(bot: commands.Bot):
    bot.add_cog(Reminder(bot))