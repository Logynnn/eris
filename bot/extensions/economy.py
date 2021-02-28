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

import random

import discord
from discord.ext import commands


class Economy(commands.Cog, name='Economia'):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.coin_emoji = bot.constants.G_COIN_EMOJI

    @commands.Cog.listener()
    async def on_first_ready(self):
        self.cache = self.bot.cache
        await self.populate_cache() 

    async def populate_cache(self):
        query = 'SELECT user_id, coins FROM profiles'
        fetch = await self.bot.manager.fetch(query)

        for record in fetch:
            user_id = record['user_id']
            coins = record['coins']

            await self.cache.set(f'economy:member:{user_id}:coins', coins)

    async def insert_user(self, ctx: commands.Context):
        member = ctx.kwargs.get('member') or ctx.author

        await self.cache.setnx(f'economy:member:{member.id}:coins', 0)

        query = 'INSERT INTO profiles VALUES ($1) ON CONFLICT (user_id) DO NOTHING'
        await ctx.bot.manager.execute(query, member.id)

    async def add_coins(self, user_id: int, coins: int):
        await self.cache.incrby(f'economy:member:{user_id}:coins', coins)

        query = 'UPDATE profiles SET coins = coins + $2 WHERE user_id = $1'
        await self.bot.manager.execute(query, user_id, coins)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.member)
    @commands.before_invoke(insert_user)
    async def daily(self, ctx: commands.Context, *, member: discord.Member = None):
        member = member or ctx.author
        to_add = random.randint(120, 160)

        await self.add_coins(member.id, to_add)

        mention = 'Você' if member == ctx.author else member.mention
        await ctx.reply(f'{mention} recebeu {to_add} {self.coin_emoji}.')

    @commands.command()
    async def bank(self, ctx: commands.Context, *, member: discord.Member = None):
        member = member or ctx.author
        mention = 'Você' if member == ctx.author else member.mention

        coins = await self.cache.get(f'economy:member:{member.id}:coins') or 0
        await ctx.reply(f'{mention} possui {coins} {self.coin_emoji}.')


def setup(bot: commands.Bot):
    bot.add_cog(Economy(bot))