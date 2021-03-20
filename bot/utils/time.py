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

import re
from datetime import datetime

import parsedatetime as pdt
from discord.ext import commands
from dateutil.relativedelta import relativedelta

from .context import ErisContext


class InvalidTime(commands.BadArgument):
    def __init__(self, message: str = 'Invalid time provided'):
        super().__init__(message)


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

    def __init__(self, argument: str, *, now: datetime = None):
        match = self.compiled.fullmatch(argument)

        if match is None or not match.group(0):
            raise InvalidTime()

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = now or datetime.utcnow()

        self.datetime = now + relativedelta(**data)

    @classmethod
    async def convert(cls, ctx: ErisContext, argument: str):
        return cls(argument, now=ctx.message.created_at)


class HumanTime:
    calendar = pdt.Calendar(pdt.Constants('pt_BR'), version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(self, argument: str, *, now: datetime = None):
        now = now or datetime.utcnow()
        dt, status = self.calendar.parseDT(argument, sourceTime=now)

        if not status.hasDateOrTime:
            raise InvalidTime()

        if not status.hasTime:
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        self.datetime = dt
        self.is_past = dt < now

    @classmethod
    async def convert(cls, ctx: ErisContext, argument: str):
        return cls(argument, now=ctx.message.created_at)


class Time(HumanTime):
    def __init__(self, argument: str, *, now: datetime = None):
        try:
            o = ShortTime(argument, now=now)
        except Exception:
            super().__init__(argument, now=now)
        else:
            self.datetime = o.datetime
            self.is_past = False


class FutureTime(Time):
    def __init__(self, argument: str, *, now: datetime = None):
        super().__init__(argument, now=now)

        if self.is_past:
            raise InvalidTime('Time is in the past')


class UserFriendlyTime(commands.Converter):
    def __init__(self, converter: commands.Converter = None, *, default: str = None):
        if isinstance(converter, type) and issubclass(converter, commands.Converter):
            converter = converter()

        if converter is not None and not isinstance(converter, commands.Converter):
            raise TypeError('Converter must be a subclass of commands.Converter')

        self.converter = converter
        self.default = default

    def copy(self) -> 'UserFriendlyTime':
        cls = type(self)
        o = cls.__new__(cls)
        o.converter = self.converter
        o.default = self.default
        return o

    async def check_constraints(self, ctx: ErisContext, now: datetime, remaining: str) -> 'UserFriendlyTime':
        if self.datetime < now:
            raise InvalidTime('This time is in the past')

        if not remaining:
            if self.default is None:
                raise commands.BadArgument('Missing argument after the time')

            remaining = self.default

        if self.converter:
            self.arg = await self.converter.convert(ctx, remaining)
        else:
            self.arg = remaining

        return self

    async def convert(self, ctx: ErisContext, argument: str):
        result = self.copy()

        calendar = HumanTime.calendar
        regex = ShortTime.compiled
        
        now = ctx.message.created_at

        match = regex.match(argument)
        if match is not None and match.group(0):
            data = {k: int(v) for k, v in match.groupdict(default=0).items()}

            remaining = argument[match.end():].strip()
            result.datetime = now + relativedelta(**data)
            return await result.check_constraints(ctx, now, remaining)

        if argument.startswith('em'):
            argument = argument[2:].strip()

        elements = calendar.nlp(argument, sourceTime=now)
        if elements is None or len(elements) == 0:
            raise InvalidTime()

        dt, status, begin, end, dt_string = elements[0]

        if not status.hasDateOrTime:
            raise InvalidTime()

        if begin not in (0, 1) and end != len(argument):
            raise InvalidTime()

        if not status.hasTime:
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        if status.accuracy == pdt.pdtContext.ACU_HALFDAY:
            dt = dt.replace(day=now.day + 1)

        result.datetime = dt

        if begin in (0, 1):
            if begin == 1:
                if argument[0] != '"':
                    raise commands.BadArgument('Expected quote before time')

                if not (end < len(argument) and argument[end] == '"'):
                    raise commands.BadArgument('If time is quoted, you must unquote it')

                remaining = argument[end + 1:].lstrip(' ,.!')
            else:
                remaining = argument[end:].lstrip(' ,.!')
        elif len(argument) == end:
            remaining = argument[:begin].strip()

        return await result.check_constraints(ctx, now, remaining)
