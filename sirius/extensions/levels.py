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
import random
import logging

import discord
from discord.ext import commands, tasks
from discord.ext.commands import CooldownMapping, BucketType

from utils import database
from utils.embed import Embed
from utils.menus import Menu


class LevelsTable(database.Table, table_name='levels'):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    exp = database.Column(database.Integer(big=True))


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        bot.loop.create_task(self.populate_cache())

        self.cache = bot.cache
        self.logger = logging.getLogger('sirius.levels')
        self.cooldown = CooldownMapping.from_cooldown(1, 60, BucketType.user)

        self._level_roles = {}
        for index, role_id in enumerate(bot.constants.LEVEL_ROLES, start=1):
            self._level_roles[index * 10] = bot.cosmic.get_role(role_id)

    @staticmethod
    def _get_level_exp(lvl: int) -> int:
        return 5 * (lvl ** 2) + 50 * lvl + 100

    @staticmethod
    def _get_level_from_exp(exp: int) -> int:
        level = 0

        while exp >= Levels._get_level_exp(level):
            exp -= Levels._get_level_exp(level)
            level += 1

        return level

    def can_receive_exp(self, channel_id: int) -> bool:
        channels = (
            self.bot.constants.GENERAL_CHANNEL_ID,
            self.bot.constants.SECONDARY_CHANNEL_ID,
            self.bot.constants.NO_MIC_CHANNEL
        )

        return channel_id in channels

    async def populate_cache(self):
        query = 'SELECT * FROM levels'
        fetch = await self.bot.manager.fetch(query)

        for record in fetch:
            user_id = record['user_id']
            exp = record['exp']

            await self.cache.sadd('levels:members', user_id)
            await self.cache.set(f'levels:member:{user_id}:exp', exp)

    async def get_user_experience(self, user_id: int) -> int:
        exp = await self.cache.get(f'levels:member:{user_id}:exp')

        if not exp:
            await self.cache.sadd('levels:members', user_id)
            await self.cache.set(f'levels:member:{user_id}:exp', 0)

            query = 'INSERT INTO levels VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING'
            await self.bot.manager.execute(query, user_id, 0)
            return 0

        return int(exp)

    async def add_experience(self, user_id: int, exp: int):
        await self.cache.incrby(f'levels:member:{user_id}:exp', exp)

        query = 'UPDATE levels SET exp = exp + $2 WHERE user_id = $1'
        await self.bot.manager.execute(query, user_id, exp)

    async def update_rewards(self, member: discord.Member):
        user_exp = await self.get_user_experience(member.id)
        user_level = Levels._get_level_from_exp(user_exp)

        await member.remove_roles(*self._level_roles, reason='Removendo cargo de níveis anteriores')

        for level, role in self._level_roles.items():
            if level > user_level:
                continue

            if role in member.roles:
                continue

        await member.add_roles(role, reason=f'Usuário subiu para o nível {level}')
        return role.mention

    @commands.command()
    async def rank(self, ctx: commands.Context):
        kwargs = {'by': 'levels:member:*:exp', 'offset': 0, 'count': -1}
        users = await self.cache.sort('levels:members', **kwargs)

        if not users:
            return await ctx.reply('Não há nada por aqui.')

        data = []
        for i, user_id in enumerate(reversed(users), start=1):
            member = ctx.guild.get_member(int(user_id))

            exp = int(await self.cache.get(f'levels:member:{user_id}:exp'))
            level = Levels._get_level_from_exp(exp)

            data.append({
                'name': f'{i}. {member}',
                'value': f'Experiência: **{exp}**\nNível: **{level}**',
                'inline': False
            })

        menu = Menu(data, paginator_type=1)
        await menu.start(ctx)

    @commands.Cog.listener()
    async def on_regular_message(self, message: discord.Message):
        if not self.can_receive_exp(message.channel.id):
            return

        now = message.created_at
        author = message.author

        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            return

        exp = await self.get_user_experience(author.id)
        level = self._get_level_from_exp(exp)

        to_add = random.randint(15, 25)
        await self.add_experience(author.id, to_add)

        new_exp = await self.get_user_experience(author.id)
        new_level = self._get_level_from_exp(new_exp)

        fmt = 'Member {0} ({0.id}) received {1} exp. ({2} -> {3})'
        self.logger.info(fmt.format(author, to_add, exp, new_exp))

        if level != new_level:
            messages = [f'Parabéns, você subiu para o nível **{new_level}**.']

            fmt = 'Member {0} ({0.id}) leveled up ({1} -> {2})'
            self.logger.info(fmt.format(author, level, new_level))

            reward = await self.update_rewards(author)
            if reward:
                messages.append(f'Ao subir neste nível você recebeu {reward}.')

            embed = Embed(description='\n'.join(messages), color=self.bot.color)
            embed.set_author(name=str(author), icon_url=author.avatar_url)

            await message.channel.send(author.mention, embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Levels(bot))
