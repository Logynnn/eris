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

from utils.menus import Menu


class ColorConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        name = '「🎨」' + argument.capitalize()
        color = discord.utils.get(ctx.guild.roles, name=name)

        if not color:
            return None

        return color if color in ctx.cog.colors else None


class Colors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.colors = [r for r in bot.cosmic.roles if r.name.startswith('「🎨」')]

    @commands.group(aliases=['colour'], invoke_without_command=True)
    async def color(self, ctx: commands.Context, *, color: ColorConverter):
        await self.color_add(ctx, color)

    @color.command(name='add')
    async def color_add(self, ctx: commands.Context, *, color: ColorConverter):
        if not color:
            return await ctx.reply('Cor não encontrada.')

        if color in ctx.author.roles:
            return await ctx.reply('Você já está com esta cor.')

        to_remove = []
        for role in ctx.author.roles:
            if role in self.colors:
                to_remove.append(role)

        await ctx.author.remove_roles(*to_remove, reason='Removendo cores anteriores')
        await ctx.author.add_roles(color, reason='Adicionando uma cor')

        message = f'Cor {color.mention} adicionada.'
        if to_remove:
            mentions = ', '.join([role.mention for role in to_remove])
            message += f'\nAs seguintes cores foram removidas: {mentions}'

        await ctx.reply(message)

    @color.command(name='list')
    async def color_list(self, ctx: commands.Context):
        roles = [role.mention for role in self.colors]

        menu = Menu(roles, per_page=12)
        await menu.start(ctx)


def setup(bot: commands.Bot):
    bot.add_cog(Colors(bot))
