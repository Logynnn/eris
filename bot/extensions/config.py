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

import logging

import discord
from discord.ext import commands

from eris import Eris
from utils import database
from utils.context import ErisContext


log = logging.getLogger(__name__)


class Configurations(database.Table):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    prefix = database.Column(database.String)


class Config(commands.Cog, name='Configurações'):
    '''Comandos relacionados a configuração do usuário.'''

    def __init__(self, bot: Eris):
        self.bot = bot
        self.no_prefix = 'Go wild, você escolheu não usar prefixo.'

    @commands.Cog.listener()
    async def on_bot_load(self):
        # Carrega os prefixos personalizados no cache.
        sql = 'SELECT user_id, prefix FROM configurations;'
        fetch = await self.bot.pool.fetch(sql)

        for record in fetch:
            user_id = record['user_id']
            prefix = record['prefix']

            await self.bot.cache.set(f'config/user/{user_id}/prefix', prefix)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Caso alguém saia do servidor, removemos
        # ela do banco de dados e do cache.
        sql = 'DELETE FROM configurations WHERE user_id = $1;'
        await self.bot.pool.execute(sql, member.id)

        await self.bot.cache.delete(f'config/user/{member.id}/prefix')

    @commands.group(invoke_without_command=True, ignore_extra=False)
    async def prefix(self, ctx: ErisContext):
        '''
        Verifica qual é o prefixo personalizado do usuário.
        Usa o prefixo padrão caso o usuário não tenha definido um.
        '''
        prefix = await self.bot.cache.get(f'config/user/{ctx.author.id}/prefix')

        if prefix is None:
            prefix = ctx.bot.default_prefix

        if prefix == '':
            message = self.no_prefix
        else:
            message = f'Seu prefixo atual é `{prefix}`.'

        await ctx.reply(message)

    @prefix.command(name='set')
    async def prefix_set(self, ctx: ErisContext, prefix: str):
        '''
        Define um prefixo personalizado para o usuário.
        '''
        if len(prefix) > 6:
            return await ctx.reply('Este prefixo é muito longo.')

        if prefix == ctx.bot.default_prefix:
            # Se o prefixo for o mesmo do padrão, então
            # nós removemos o prefixo da pessoa do cache
            # e do banco de dados.
            sql = 'DELETE FROM configurations WHERE user_id = $1;'
            await ctx.pool.execute(sql, ctx.author.id)

            await ctx.cache.delete(f'config/user/{ctx.author.id}/prefix')
        elif prefix == 'eris ':
            # Este já é um prefixo global então falamos que o usuário
            # não pode usar este prefixo.
            return await ctx.reply('Este já é um prefixo global.')
        else:
            sql = 'UPDATE configurations SET prefix = $2 WHERE user_id = $1;'
            await ctx.pool.execute(sql, ctx.author.id, prefix)

            await ctx.cache.set(f'config/user/{ctx.author.id}/prefix', prefix)

        log.info(f'User {ctx.author} ({ctx.author.id}) changed his/her custom prefix to "{prefix}".')

        if prefix == '':
            message = self.no_prefix
        else:
            message = f'Você alterou seu prefixo para `{prefix}`.'

        await ctx.reply(message)


def setup(bot: Eris):
    bot.add_cog(Config(bot))
