import datetime
import random

import discord
from discord.ext import commands, tasks

from utils import database
from utils.embed import Embed


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

class LevelsTable(database.Table, table_name='levels'):
    user_id = database.Column(database.Integer(big=True), primary_key=True)

    exp = database.Column(database.Integer(big=True))
    last_message = database.Column(database.Datetime)

class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._level_roles = {}
        for i, id_ in enumerate(LEVEL_ROLES, start=1):
            self._level_roles[i * 10] = bot.cosmic.get_role(id_)

    @staticmethod
    def _get_level_exp(lvl: int) -> int:
        return 5 * (lvl ** 2) + 50 * lvl + 100

    @staticmethod
    def _get_level_from_exp(exp: int) -> int:
        level = 0

        while exp >= LevelSystem._get_level_exp(level):
            exp -= LevelSystem._get_level_exp(level)
            level += 1

        return level

    async def populate_cache(self):
        query = 'SELECT * FROM levels'
        fetch = await self.bot.manager.fetch(query)

        self._cache = {}

        for record in fetch:
            data = {'exp': record['exp'], 'last_message': record['last_message']}
            self._cache[record['user_id']] = data

    async def get_profile(self, member: discord.Member):
        try:
            profile = self._cache[member.id]
        except KeyError:
            now = datetime.datetime.utcnow()

            profile = {'exp': 0, 'last_message': now}
            self._cache[member.id] = profile

            query = 'INSERT INTO levels VALUES ($1, $2, $3)'
            await self.bot.manager.execute(query, member.id, 0, now)
        finally:
            return profile

    async def add_experience(self, user_id: int, exp: int, *, now: datetime.datetime):
        profile = self._cache[user_id]

        profile['exp'] += exp
        profile['last_message'] = now

        query = 'UPDATE levels SET exp = exp + $2, last_message = $3 WHERE user_id = $1'
        await self.bot.manager.execute(query, user_id, exp, now)

    async def update_rewards(self, member: discord.Member):
        profile = self._cache[member.id]
        rewards = []

        user_level = LevelSystem._get_level_from_exp(profile['exp'])

        for level, role in self._level_roles.items():
            if level > user_level:
                continue

            if role in member.roles:
                continue

            rewards.append(role)
            await member.add_roles(role, reason=f'Usuário subiu para o nível {level}')

        return rewards

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not hasattr(self, '_cache'):
            await self.populate_cache()

        now = message.created_at
        author = message.author

        profile = await self.get_profile(author)

        delta = now - profile['last_message']
        if not delta.total_seconds() >= 60:
            return

        exp = random.randint(15, 25)
        level = self._get_level_from_exp(profile['exp'])

        await self.add_experience(author.id, exp, now=now)

        new_level = self._get_level_from_exp(profile['exp'])
        if level != new_level:
            messages = [f'Parabéns, você subiu para o nível **{new_level}**.']

            rewards = await self.update_rewards(author)
            if rewards:
                roles = [role.mention for role in rewards]
                messages.append('Ao subir neste nível você recebeu %s.' % ', '.join(roles))

            embed = Embed(
                description='\n'.join(messages),
                author={'name': str(author), 'icon_url': author.avatar_url},
                color=message.guild.me.color
            )

            await message.channel.send(author.mention, embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(Levels(bot))