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
import logging
from typing import Optional

import discord
from discord import Member
from discord.ext import commands
from discord.ext.commands import CooldownMapping, BucketType

from eris import Eris
from utils import database
from utils import checks
from utils.context import ErisContext
from utils.human import suffix_number
from utils.menus import ErisMenuPages, SourceType


log = logging.getLogger(__name__)


GENERAL_CHANNEL_ID   = 810910658458550303
SECONDARY_CHANNEL_ID = 810910918078627880
NO_MIC_CHANNEL_ID    = 812729768075984956

LEVEL_ROLES = (
    799358067233521665,
    799358068055474187,
    799358069275623434,
    799358070273605682,
    799358071184425031,
    799358072325144656,
    799358073319194704,
    799358074346274846,
    799358846937464922,
    799367386695991407
)


class Levels(database.Table):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    exp = database.Column(database.Integer, default=0)


class Ranking(commands.Cog):
    '''Comandos relacionados ao sistema de níveis.'''

    def __init__(self, bot: Eris):
        self.bot = bot
        self.cooldown = CooldownMapping.from_cooldown(1, 60, BucketType.member)

    @staticmethod
    def get_level_exp(level: int) -> int:
        return 5 * (level ** 2) + 50 * level + 100

    @staticmethod
    def get_total_exp(level: int) -> int:
        total_exp = 0

        for i in range(level):
            total_exp += Ranking.get_level_exp(i)

        return total_exp

    @staticmethod
    def get_level_from_exp(exp: int) -> int:
        level = 0

        while exp >= Ranking.get_level_exp(level):
            exp -= Ranking.get_level_exp(level)
            level += 1

        return level

    @commands.Cog.listener()
    async def on_bot_load(self):
        # Carrega os dados dos usuários no cache.
        sql = 'SELECT user_id, exp FROM levels;'
        fetch = await self.bot.pool.fetch(sql)

        for record in fetch:
            user_id = record['user_id']
            exp = record['exp']

            # Adiciona o usuário na lista de usuários assim
            # podemos ordenar na hora de mostrar o ranking.
            await self.bot.cache.sadd('levels/users', user_id)
            await self.bot.cache.set(f'levels/user/{user_id}/exp', exp)

    @commands.Cog.listener()
    async def on_first_launch(self):
        # Define os níveis e os cargos de níveis.
        self.roles = {}

        for i, role_id in enumerate(LEVEL_ROLES, start=1):
            self.roles[i * 10] = self.bot.cosmic.get_role(role_id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        # Caso alguém saia do servidor, removemos
        # ela do banco de dados e do cache.
        sql = 'DELETE FROM levels WHERE user_id = $1;'
        await self.bot.pool.execute(sql, member.id)

        await self.bot.cache.delete(f'levels/user/{member.id}/exp')
        await self.bot.cache.srem('level/users', member.id)

    @commands.Cog.listener()
    async def on_regular_message(self, message: discord.Message):
        if not self.can_receive_exp(message.channel.id):
            return

        author = message.author

        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            return

        exp = await self.get_user_experience(author.id)
        level = self.get_level_from_exp(exp)

        # Se o usuário for nível 100 então não iremos dar exp.
        if level >= 100:
            return

        to_add = random.randint(15, 25)
        await self.add_experience(author.id, to_add)

        new_exp = await self.get_user_experience(author.id)
        new_level = self.get_level_from_exp(new_exp)

        fmt = 'User {0} ({0.id}) received {1} exp. ({2} -> {3})'
        log.info(fmt.format(author, to_add, exp, new_exp))

        # Se ao receber exp. o nível do usuário mudou,
        # significa que ele subiu de nível.
        if level != new_level:
            messages = [f'Parabéns, você subiu para o nível **{new_level}**.']

            fmt = 'User {0} ({0.id}) leveled up ({1} -> {2})'
            log.info(fmt.format(author, level, new_level))

            reward = await self.update_rewards(author)

            if reward:
                messages.append(f'Ao subir para este nível você recebeu {reward}.')

            embed = discord.Embed(description='\n'.join(messages), colour=0x2f3136)
            embed.set_author(name=author.display_name, icon_url=author.avatar_url)

            await message.reply(embed=embed, mention_author=False)

    def can_receive_exp(self, channel_id: int) -> bool:
        '''Retorna um booleano que diz se o canal pode ou não receber experiência.

        Parameters
        ----------
        channel_id: :class:`int`
            O ID do canal.

        Returns
        -------
        :class:`bool`
            Um booleano que indica se o canal pode receber experiência.
        '''        
        return channel_id in (GENERAL_CHANNEL_ID, SECONDARY_CHANNEL_ID, NO_MIC_CHANNEL_ID)

    async def insert_user(self, user_id: int):
        '''Insere um usuário no banco de dados.
        Caso o usuário já exista então nada é feito.

        Parameters
        ----------
        user_id : int
            [description]
        '''
        sql = '''
            INSERT INTO levels
            VALUES ($1)
            ON CONFLICT (user_id)
            DO NOTHING;
        '''
        await self.bot.pool.execute(sql, user_id)

        await self.bot.cache.sadd('levels/users', user_id)
        await self.bot.cache.setnx(f'levels/user/{user_id}/exp', 0)

    async def get_user_experience(self, user_id: int) -> int:
        '''Mostra a quantidade de experiência que um usuário tem.
        Retorna `0` caso o usuário não esteja no cache.

        Parameters
        ----------
        user_id: :class:`int`
            O ID do usuário.

        Returns
        -------
        :class:`int`
            A quantidade de experiência que o usuário possui.
        '''        
        exp = await self.bot.cache.get(f'levels/user/{user_id}/exp')

        # Caso o usuário não esteja no cache, então admitimos
        # que ele também não esteja no banco de dados. Podemos
        # retornar zero.
        if not exp:
            return 0

        return int(exp)

    async def add_experience(self, user_id: int, exp: int):
        '''Adiciona uma quantidade de experiência em um usuário.
        Caso o usuário não esteja no cache então ele é inserido
        tanto no cache quanto no banco de dados.


        Parameters
        ----------
        user_id: :class:`int`
            O ID do usuário.
        exp: :class:`int`
            A quantidade de experiência a ser dada.
        '''
        await self.insert_user(user_id)

        sql = 'UPDATE levels SET exp = exp + $2 WHERE user_id = $1;'
        await self.bot.pool.execute(sql, user_id, exp)

        await self.bot.cache.incrby(f'levels/user/{user_id}/exp', exp)

    async def remove_experience(self, user_id: int, exp: int):
        '''Remove uma quantidade de experiência em um usuário.
        Caso o usuário não esteja no cache então ele é inserido
        tanto no cache quanto no banco de dados.

        Parameters
        ----------
        user_id: :class:`int`
            O ID do usuário.
        exp: :class:`int`
            A quantidade de experiência a ser removida.
        '''
        await self.insert_user(user_id)

        sql = 'UPDATE levels SET exp = exp - $2 WHERE user_id = $1;'
        await self.bot.pool.execute(sql, user_id, exp)

        await self.bot.cache.decrby(f'levels/user/{user_id}/exp', exp)

    async def set_experience(self, user_id: int, exp: int):
        '''Define uma quantidade de experiência em um usuário.
        Caso o usuário não esteja no cache então ele é inserido
        tanto no cache quanto no banco de dados.

        Parameters
        ----------
        user_id: :class:`int`
            O ID do usuário.
        exp: :class:`int`
            A quantidade de experiência a ser definida.
        '''
        await self.insert_user(user_id)

        sql = 'UPDATE levels SET exp = $2 WHERE user_id = $1;'
        await self.bot.pool.execute(sql, user_id, exp)

        await self.bot.cache.set(f'levels/user/{user_id}/exp', exp)

    async def update_rewards(self, member: Member):
        '''Atualiza os cargos de recompensa.

        Parameters
        ----------
        member: :class:`discord.Member`
            O usuário a ser recompensado.
        '''
        exp = await self.get_user_experience(member.id)
        level = self.get_level_from_exp(exp)

        roles = self.roles.values()
        await member.remove_roles(*roles, reason='Removendo cargo de níveis anteriores')

        role = self.roles.get(level)

        if not role:
            return None

        await member.add_roles(role, reason=f'Usuário subiu para o nível {level}')
        return role.mention

    @commands.command(aliases=['ranking', 'top'], ignore_extra=False)
    async def rank(self, ctx: ErisContext):
        '''
        Mostra o ranking do servidor.
        '''

        # Usamos a key `levels/users` para ordenar o padrão `levels/user/<id>/exp`.
        users = await ctx.cache.sort('levels/users', by='levels/user/*/exp', asc=False)

        if not users:
            return await ctx.reply('Não há nada por aqui.')

        entries = []

        for i, user_id in enumerate(users, start=1):
            member = ctx.guild.get_member(int(user_id))

            exp = int(await ctx.cache.get(f'levels/user/{user_id}/exp'))
            level = self.get_level_from_exp(exp)

            value = f'Experiência: **{suffix_number(exp)}**\nNível: **{level}**'
            field = {'name': f'{i}. {member.display_name}', 'value': value}
            entries.append(field)

        menu = ErisMenuPages(entries, source=SourceType.FIELD, per_page=6)
        await menu.start(ctx)

    @commands.group(invoke_without_command=True)
    async def exp(self, ctx: ErisContext, *, member: discord.Member = None):
        '''
        Verifica a quantidade de exp. e o nível um usuário tem.
        '''
        member = member or ctx.author

        await self.insert_user(member.id)

        exp = int(await ctx.cache.get(f'levels/user/{member.id}/exp'))
        level = self.get_level_from_exp(exp)

        diff_exp = exp - self.get_total_exp(level)
        needed_exp = self.get_level_exp(level + 1)

        percentage = ctx.get_percentage(diff_exp, needed_exp)
        bar = ctx.progress_bar(percentage)

        title = f'Experiência de {member.display_name}'
        content = f'Experiência: **{suffix_number(exp)}**\nNível: **{level}**\n\n{bar}'

        await ctx.reply(content, title=title)

    @exp.command(name='add')
    @checks.is_staffer()
    async def exp_add(self, ctx: ErisContext, member: Optional[Member] = None, exp: int = None):
        '''
        Adiciona um número de exp. em um usuário.
        '''
        if exp is None or exp < 0:
            return await ctx.reply('Diga um valor válido para eu adicionar.')

        member = member or ctx.author

        await self.add_experience(member.id, exp)
        await ctx.reply(f'Você adicionou `{exp}` de exp. para {member.mention}.')

    @exp.command(name='remove')
    @checks.is_staffer()
    async def exp_remove(self, ctx: ErisContext, member: Optional[Member] = None, exp: int = None):
        '''
        Remove um número de níveis de um usuário.
        '''
        if exp is None or exp < 0:
            return await ctx.reply('Diga um valor válido para eu remover.')

        member = member or ctx.author

        await self.remove_experience(member.id, exp)
        await ctx.reply(f'Você removeu `{exp}` de exp. de {member.mention}.')

    @exp.command(name='set')
    @checks.is_staffer()
    async def exp_set(self, ctx: ErisContext, member: Optional[Member] = None, exp: int = None):
        '''
        Altera o nível de um usuário.
        '''
        if exp is None or exp < 0:
            return await ctx.reply('Diga um valor válido para eu definir.')

        member = member or ctx.author

        await self.set_experience(member.id, exp)
        await ctx.reply(f'Você alterou a exp. de {member.mention} para `{exp}`.')


def setup(bot: Eris):
    bot.add_cog(Ranking(bot))
