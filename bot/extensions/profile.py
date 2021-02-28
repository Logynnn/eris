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

import discord
from discord.ext import commands

from utils import database
from .crates import raw


class Profiles(database.Table):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    coins = database.Column(database.Integer(big=True), default=0)

    default = "'{\"crates\": {}}'::jsonb"
    inventory = database.Column(database.JSON, default=default)


class Profile(commands.Cog, name='Perfil'):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.coin_emoji = bot.constants.G_COIN_EMOJI

    @commands.command(aliases=['inv'])
    async def inventory(self, ctx: commands.Context):
        query = 'SELECT * FROM profiles WHERE user_id = $1'
        fetch = await self.bot.manager.fetch_row(query, ctx.author.id)

        coins = fetch['coins']
        inventory = fetch['inventory']

        crates_list = []
        for name, count in inventory['crates'].items():
            crate = raw[name]
            emoji = crate['emoji']

            crates_list.append(f'{count}x {emoji}')

        embed = discord.Embed(title='Seu inventário', color=ctx.bot.color)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        crates = ', '.join(crates_list) or 'Não possui caixas.'
        embed.add_field(name='Caixas', value=crates, inline=False)

        coins = f'{coins} {self.coin_emoji}'
        embed.add_field(name='G-Coins', value=coins)

        await ctx.reply(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Profile(bot))