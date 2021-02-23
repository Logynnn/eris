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

import locale

import discord
from discord.ext import commands, tasks

from utils import database
from utils.embed import Embed


class MostActive(database.Table, table_name='most_active'):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    messages = database.Column(database.Integer)


class Rewards(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.give_rewards.start()

    def cog_unload(self):
        self.give_rewards.cancel()

    @commands.Cog.listener()
    async def on_first_ready(self):
        self.cosmic = self.bot.cosmic
        self.general_channel = self.bot.general_channel

    @property
    def reward_role(self) -> discord.Role:
        return self.cosmic.get_role(self.bot.constants.REWARD_ROLE_ID)

    @tasks.loop(hours=168)
    async def give_rewards(self):
        if self._first:
            self._first = False
            return

        query = 'SELECT user_id, messages FROM most_active ORDER BY messages DESC LIMIT 1'
        fetch = await self.bot.manager.fetch_row(query)

        user = self.cosmic.get_member(fetch[0])

        for member in reward_role.members:
            await member.remove_roles(reward_role, reason='Removendo cargo de membro mais ativo da semana')

        total_messages = f'{fetch[1]:,}'.replace(',', '.')
        description = f'{user.mention} é o membro mais ativo da semana com **{total_messages} mensagens**.'

        embed = Embed(
            title='Novo tagarela da semana!',
            description=description,
            color=self.bot.color
        )

        query = 'DELETE FROM most_active'
        await self.bot.manager.execute(query)

        await user.add_roles(reward_role, reason='Adicionando cargo de membro mais ativo da semana')
        await self.bot.general_channel.send(embed=embed)

    @give_rewards.before_loop
    async def before_give_rewards(self):
        self._first = True

    async def populate_cache(self):
        query = 'SELECT * FROM most_active'
        fetch = await self.bot.manager.fetch(query)

        self._cache = {}

        for record in fetch:
            self._cache[record['user_id']] = record['messages']

    async def insert(self, member: discord.Member):
        query = 'INSERT INTO most_active VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING'
        await self.bot.manager.execute(query, member.id, 1)

        self._cache[member.id] = 1

    @commands.Cog.listener()
    async def on_regular_message(self, message: discord.Message):
        if not hasattr(self, '_cache'):
            await self.populate_cache()

        author = message.author

        if author.id not in self._cache:
            return await self.insert(author)

        query = 'UPDATE most_active SET messages = messages + 1 WHERE user_id = $1'
        await self.bot.manager.execute(query, author.id)

        self._cache[author.id] += 1


def setup(bot: commands.Bot):
    bot.add_cog(Rewards(bot))
