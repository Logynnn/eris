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

import random
from typing import Optional

import discord
from discord import Member
from discord.ext import commands

from eris import Eris
from utils import database
from utils import checks
from utils.context import ErisContext


COIN_EMOJI = '<:Ten:820727174424166530>'


class Currency(database.Table):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    coins = database.Column(database.Integer(big=True), default=0)


class Economy(commands.Cog, name='Economia'):
    '''Comandos relacionados à economia do servidor.'''

    def __init__(self, bot: Eris):
        self.bot = bot

    @commands.Cog.listener()
    async def on_load(self):
        # Carrega os dados dos usuários no cache.
        sql = 'SELECT user_id, coins FROM currency;'
        fetch = await self.bot.pool.fetch(sql)

        for record in fetch:
            user_id = record['user_id']
            coins = record['coins']

            await self.bot.cache.set(f'economy/user/{user_id}/coins', coins)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Caso alguém saia do servidor, removemos
        # ela do banco de dados e do cache.
        sql = 'DELETE FROM currency WHERE user_id = $1;'
        await self.bot.pool.execute(sql, member.id)

        await self.bot.cache.delete(f'economy/user/{member.id}/coins')

    async def insert_user(self, ctx: ErisContext):
        member = ctx.kwargs.get('member') or ctx.author

        sql = 'INSERT INTO currency VALUES ($1) ON CONFLICT (user_id) DO NOTHING;'
        await ctx.pool.execute(sql, member.id)

        await ctx.cache.setnx(f'economy/user/{member.id}/coins', 0)

    async def add_coins(self, user_id: int, coins: int):
        sql = 'UPDATE currency SET coins = coins + $2 WHERE user_id = $1;'
        await self.bot.pool.execute(sql, user_id, coins)

        await self.bot.cache.incrby(f'economy/user/{user_id}/coins', coins)

    async def remove_coins(self, user_id: int, coins: int):
        sql = 'UPDATE currency SET coins = coins - $2 WHERE user_id = $1;'
        await self.bot.pool.execute(sql, user_id, coins)

        await self.bot.cache.decrby(f'economy/user/{user_id}/coins', coins)

    async def set_coins(self, user_id: int, coins: int):
        sql = 'UPDATE currency SET coins = $2 WHERE user_id = $1;'
        await self.bot.pool.execute(sql, user_id, coins)

        await self.bot.cache.set(f'economy/user/{user_id}/coins', coins)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.member)
    @commands.before_invoke(insert_user)
    async def daily(self, ctx: ErisContext, *, member: Member = None):
        '''
        Receba seus tens diários (ou doe eles para alguém).
        '''
        member = member or ctx.author

        to_add = random.randint(120, 160)
        await self.add_coins(member.id, to_add)

        await ctx.reply(f'{member.mention} recebeu {to_add} {COIN_EMOJI}.')

    @commands.group(invoke_without_command=True, aliases=['balance', 'bal', 'tens', 'coins'])
    async def bank(self, ctx: ErisContext, *, member: Member = None):
        '''
        Veja a seu saldo (ou o saldo de outra pessoa).
        '''
        member = member or ctx.author

        coins = await ctx.cache.get(f'economy/user/{member.id}/coins') or 0
        await ctx.reply(f'{member.mention} possui {coins} {COIN_EMOJI}.')

    @bank.command(name='add')
    @checks.is_staffer()
    async def bank_add(self, ctx: ErisContext, member: Optional[Member] = None, amount: int = None):
        '''
        Adiciona um valor ao saldo de um usuário.
        '''
        if amount is None or amount < 0:
            return await ctx.reply('Diga um valor válido para eu adicionar.')

        member = member or ctx.author

        await self.add_coins(member.id, amount)
        await ctx.reply(f'Você adicionou {amount} {COIN_EMOJI} ao saldo de {member.mention}.')

    @bank.command(name='remove')
    @checks.is_staffer()
    async def bank_remove(self, ctx: ErisContext, member: Optional[Member] = None, amount: int = None):
        '''
        Remove um valor do saldo de um usuário.
        '''
        if amount is None or amount < 0:
            return await ctx.reply('Diga um valor válido para eu remover.')

        member = member or ctx.author

        await self.remove_coins(member.id, amount)
        await ctx.reply(f'Você removeu {amount} {COIN_EMOJI} do saldo de {member.mention}.')

    @bank.command(name='set')
    @checks.is_staffer()
    async def bank_set(self, ctx: ErisContext, member: Optional[Member] = None, amount: int = None):
        '''
        Altere o valor do saldo de um usuário.
        '''
        if amount is None or amount < 0:
            return await ctx.reply('Diga um valor válido para eu definir.')

        member = member or ctx.author

        await self.set_coins(member.id, amount)
        await ctx.reply(f'Você alterou o saldo de {member.mention} para {amount} {COIN_EMOJI}.')


def setup(bot: Eris):
    bot.add_cog(Economy(bot))
