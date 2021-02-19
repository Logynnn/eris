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

import datetime
import re

import parsedatetime as pdt
from discord.ext import commands
from unidecode import unidecode
from dateutil.relativedelta import relativedelta


class ShortTime:
    compiled = re.compile(r'''
        (?:(?P<years>[0-9]{1,9})\s?(?:anos?))?
        (?:(?P<months>[0-9]{1,9})\s?(?:mes(?:es)?))?
        (?:(?P<weeks>[0-9]{1,9})\s?(?:semanas?))?
        (?:(?P<days>[0-9]{1,9})\s?(?:dias?|d))?
        (?:(?P<hours>[0-9]{1,9})\s?(?:horas?|h))?
        (?:(?P<minutes>[0-9]{1,9})\s?(?:minutos?|m(?:ins?)?))?
        (?:(?P<seconds>[0-9]{1,9})\s?(?:segundos?|s(?:egs?)?))?
    ''', re.VERBOSE)

    def __init__(self, argument: str, *, now: datetime.datetime = None):
        argument = unidecode(argument)
        match = self.compiled.fullmatch(argument)

        if match is None or not match.group(0):
            raise commands.BadArgument('Invalid time provided')

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = now or datetime.datetime.utcnow()

        self.datetime = now + relativedelta(**data)

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str):
        return cls(argument, now=ctx.message.created_at)


class HumanTime:
    calendar = pdt.Calendar(
        pdt.Constants('pt_BR'),
        version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(self, argument: str, *, now: datetime.datetime = None):
        argument = unidecode(argument)

        now = now or datetime.datetime.utcnow()
        dt, status = self.calendar.parseDT(argument, sourceTime=now)

        if not status.hasDateOrTime:
            raise commands.BadArgument('Invalid time provided')

        if not status.hasTime:
            dt = dt.replace(
                hour=now.hour,
                minute=now.minute,
                second=now.second,
                microsecond=now.microsecond)

        self.datetime = dt
        self._past = dt < now

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str):
        return cls(argument, now=ctx.message.created_at)


class Time(HumanTime):
    def __init__(self, argument: str, *, now: datetime.datetime = None):
        argument = unidecode(argument)

        try:
            o = ShortTime(argument, now=now)
        except Exception:
            super().__init__(argument, now=now)
        else:
            self.datetime = o.datetime
            self._past = False


class FutureTime(Time):
    def __init__(self, argument: str, now: datetime.datetime = None):
        super().__init__(argument, now=now)

        if self._past:
            raise commands.BadArgument('Time is in the past')
