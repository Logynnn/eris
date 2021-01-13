from discord.ext import commands

from .embed import Embed


class Context(commands.Context):
    def get_embed(self, content: str=None, **kwargs) -> Embed:
        '''Cria uma ``Embed`` automaticamente e a retorna.'''
        author = {'icon_url': self.author.avatar_url, 'name': self.author.display_name}
        color = self.guild.me.color
        return Embed(description=content, author=author, color=color, **kwargs)

    async def reply(self, content: str=None, **kwargs):
        '''Este método foi sobrescrito para enviar ``Embed`` automaticamente.'''
        return await super().reply(embed=self.get_embed(content, **kwargs))