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

import functools
from typing import Callable

from discord.ext import commands

from .constants import PREMIUM_ROLES


def is_premium():
    def predicate(ctx: commands.Context):
        return any(role in ctx.bot.premium_roles for role in ctx.author.roles)

    return commands.check(predicate)


def is_staffer():
    def predicate(ctx: commands.Context):
        return ctx.bot.staff_role in ctx.author.roles

    return commands.check(predicate)


def is_guild_owner():
    def wrapper(func: Callable):
        @functools.wraps(func)
        async def wrapped(self, ctx: commands.Context, *args, **kwargs):
            guild = await self.get_guild(ctx, ctx.author.id)

            if not guild:
                return await ctx.reply('Você não possui uma guilda.')

            if guild.owner != ctx.author:
                return await ctx.reply('Você não é o dono desta guilda.')

            ctx.member_guild = guild
            return await func(self, ctx, *args, **kwargs)
        return wrapped
    return wrapper
