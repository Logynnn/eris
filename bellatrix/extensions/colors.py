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
        self.colors = [role for role in bot.cosmic.roles if role.name.startswith('「🎨」')]

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