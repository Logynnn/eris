from discord.ext import commands

from .embed import Embed
from .menus import ConfirmMenu


class Context(commands.Context):
    def get_embed(self, content: str=None, **kwargs) -> Embed:
        '''Cria uma ``Embed`` automaticamente e a retorna.'''
        author = {'icon_url': self.author.avatar_url, 'name': self.author.display_name}
        color = kwargs.pop('color', None)

        if not color or color == 0:
            color = self.guild.me.color

        return Embed(description=content, author=author, color=color, **kwargs)

    async def reply(self, content: str=None, **kwargs):
        '''Este método foi sobrescrito para enviar ``Embed`` automaticamente.'''
        embed = kwargs.get('embed', self.get_embed(content, **kwargs))
        return await super().reply(embed=embed)

    async def prompt(self, content: str):
        menu = ConfirmMenu(content)
        return await menu.prompt(self)
