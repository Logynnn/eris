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
import asyncio
from textwrap import indent, dedent

import discord
from discord.ext import commands, tasks


raw = {
    'wooden_crate': {
        'fancy_name': 'Caixa de Madeira',
        'emoji': '<:WoodenCrate:813475171859955785>',
        'image': 'https://i.imgur.com/wmeHKBd.png',
        'items': [
            {
                'weight': 0.6,
                'func': 'give_coins',
                'args': (100, 150)
            }
        ]
    }
}


class Crate:
    def __init__(self, name: str, *, bot: commands.Bot):
        self.name = name
        self.bot = bot

        crate = raw[name]
        self.fancy_name = crate['fancy_name']
        self.emoji = crate['emoji']
        self.image = crate['image']
        self.items = crate['items']

    async def add_to_member(self, member: discord.Member):
        query = '''
            UPDATE profiles
            SET inventory = (
                CASE
                    WHEN inventory#>'{crates,name}' IS NOT NULL
                        THEN jsonb_set(inventory, '{crates,name}', (
                            (inventory#>>'{crates,name}')::int + 1)::text::jsonb
                        )
                    ELSE jsonb_insert(inventory, '{crates,name}', '1')
                END
            )
            WHERE user_id = $1
        '''.replace('name', self.name)
        await self.bot.manager.execute(query, member.id)

    async def open(self, ctx: commands.Context):
        query = "SELECT inventory->'crates'->$2 AS count FROM profiles WHERE user_id = $1"
        fetch = await ctx.bot.manager.fetch_row(query, ctx.author.id, self.name)

        if not fetch or fetch['count'] <= 0:
            return await ctx.reply('Você não possui esta caixa.')

        weights = [item['weight'] for item in self.items]
        item = random.choices(self.items, weights=weights)[0]

        func = getattr(self, f'_{item["func"]}')
        args = item['args']

        await func(ctx, *args)

        query = '''
            UPDATE profiles
            SET inventory = (
                jsonb_set(inventory, '{crates,name}', (
                    (inventory#>>'{crates,name}')::int - 1)::text::jsonb
                )
            )
            WHERE user_id = $1
        '''.replace('name', self.name)
        await self.bot.manager.execute(query, ctx.author.id)

    # rewards
    async def _give_coins(self, ctx: commands.Context, min: int, max: int):
        to_add = random.randint(min, max)
        coin_emoji = ctx.bot.constants.G_COIN_EMOJI

        query = 'UPDATE profiles SET coins = coins + $2 WHERE user_id = $1'
        await ctx.bot.manager.execute(query, ctx.author.id, to_add)

        await ctx.reply(f'Você recebeu {to_add} {coin_emoji} ao abrir esta caixa.')


class DroppableCrate(Crate):
    def __init__(self, name: str, *, bot: commands.Bot):
        self.name = name
        self.bot = bot

        crate = raw[name]
        self.fancy_name = crate['fancy_name']
        self.emoji = crate['emoji']
        self.image = crate['image']

        self.emojis = ['😴', '🦆', '🍘', '🍆', '🪁', '🛸', '🪑']

        self.title = 'Em meio a conversa, vocês se deparam com uma caixa!'
        self.description = 'Reaja com {emoji} para reivindicar esta caixa.'

    async def drop(self, channel: discord.TextChannel):
        bot = channel.guild.me
        emoji = random.choice(self.emojis)

        description = self.description.format(emoji=emoji)

        embed = discord.Embed(title=self.title, description=description, color=self.bot.color)
        embed.set_image(url=self.image)

        message = await channel.send(embed=embed)

        def reaction_check(reaction: discord.Reaction, user: discord.Member):
            return reaction.message == message and str(reaction.emoji) in self.emojis

        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=reaction_check, timeout=20)
        except asyncio.TimeoutError:
            return await message.delete()
        else:
            await message.delete()
            await self.add_to_member(user)

            description = 'Parabéns, a caixa foi adicionada em seu inventário.'
            embed = discord.Embed(description=description, color=self.bot.color)
            embed.set_author(name=str(user), icon_url=user.avatar_url)

            await channel.send(user.mention, embed=embed)


class CrateConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        return Crate(argument, bot=ctx.bot)


class Crates(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.drop_crate.start()

    @tasks.loop(minutes=30)
    async def drop_crate(self):
        await self.crate.drop(self.channel)

        minutes = random.randint(20, 60)
        self.drop_crate.change_interval(minutes=minutes)

    @drop_crate.before_loop
    async def before_drop_crate(self):
        await self.bot.wait_until_ready()

        self.channel = self.bot.general_channel
        self.crate = DroppableCrate('wooden_crate', bot=self.bot)

    @commands.group()
    async def crates(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(self.crates)

    @crates.command(name='open')
    async def crates_open(self, ctx: commands.Context, crate: CrateConverter):
        await crate.open(ctx)


def setup(bot: commands.Bot):
    bot.add_cog(Crates(bot))