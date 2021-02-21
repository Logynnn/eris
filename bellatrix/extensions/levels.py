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

import discord
from discord.ext import commands, tasks
from discord.ext.commands import CooldownMapping, BucketType

from utils import database
from utils.embed import Embed
from utils.menus import Menu


class LevelsTable(database.Table, table_name='levels'):
    user_id = database.Column(database.Integer(big=True), primary_key=True)

    exp = database.Column(database.Integer(big=True))
    last_message = database.Column(database.Datetime)


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache = bot.cache

        self.cooldown = CooldownMapping.from_cooldown(1, 60, BucketType.user)

        bot.loop.create_task(self.populate_cache())

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

    @commands.command()
    async def rank(self, ctx: commands.Context):
        query = 'SELECT * FROM levels ORDER BY exp DESC'
        fetch = await self.bot.manager.fetch(query)

        data = []
        for i, record in enumerate(fetch, start=1):
            member = ctx.guild.get_member(record['user_id'])
            exp = record['exp']
            level = Levels._get_level_from_exp(exp)

            field = {
                'name': f'{i}. {member}',
                'value': f'Experiência: **{exp}**\nNível: **{level}**',
                'inline': False
            }
            data.append(field)

        if not data:
            return await ctx.reply('Não há nada por aqui.')

        menu = Menu(data, paginator_type=1)
        await menu.start(ctx)

    async def populate_cache(self):
        query = 'SELECT * FROM levels'
        fetch = await self.bot.manager.fetch(query)

        for record in fetch:
            user_id = record['user_id']
            exp = record['exp']

            print(user_id, exp)
            await self.cache.set(f'levels:{user_id}:exp', exp)

    async def get_user_experience(self, user_id: int) -> int:
        exp = await self.cache.get(f'levels:{user_id}:exp')

        if not exp:
            await self.cache.set(f'levels:{user_id}:exp', 0)

            query = 'INSERT INTO levels VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING'
            await self.bot.manager.execute(query, user_id, 0)

            return 0

        return int(exp)

    async def add_experience(self, user_id: int, exp: int):
        await self.cache.incrby(f'levels:{user_id}:exp', exp)

        query = 'UPDATE levels SET exp = exp + $2 WHERE user_id = $1'
        await self.bot.manager.execute(query, user_id, exp)

    async def update_rewards(self, member: discord.Member):
        given = []

        user_exp = self.get_user_experience(member.id)
        user_level = Levels._get_level_from_exp(user_exp)

        for level, role in self._level_roles.items():
            if level > user_level:
                continue

            if role in member.roles:
                continue

            given.append(role.mention)
            await member.add_roles(role, reason=f'Usuário subiu para o nível {level}')

        return rewards

    @commands.Cog.listener()
    async def on_regular_message(self, message: discord.Message):
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
        if level != new_level:
            messages = [f'Parabéns, você subiu para o nível **{new_level}**.']

            rewards = await self.update_rewards(author)
            if rewards:
                messages.append(
                    'Ao subir neste nível você recebeu %s.' %
                    ', '.join(roles))

            embed = Embed(
                description='\n'.join(messages),
                author={'name': str(author), 'icon_url': author.avatar_url},
                color=self.bot.color
            )

            await message.channel.send(author.mention, embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Levels(bot))
