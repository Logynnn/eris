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
from discord.ext import commands, menus

from typing import List, Mapping


class _MenuBase(menus.Menu):
    async def update(self, payload: discord.RawReactionActionEvent):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            else:
                return

        await super().update(payload)


class _MenuPagesBase(menus.MenuPages):
    async def update(self, payload: discord.RawReactionActionEvent):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            else:
                return

        await super().update(payload)


class ConfirmMenu(_MenuBase):
    def __init__(self, content: str):
        super().__init__(delete_message_after=True)
        self.content = content
        self.result = None

    async def send_initial_message(self, ctx: commands.Context, _):
        return await ctx.reply(self.content)

    @menus.button('✅')
    async def on_confirm(self, payload: discord.RawReactionActionEvent):
        self.result = True
        self.stop()

    @menus.button('❌')
    async def on_deny(self, payload: discord.RawReactionActionEvent):
        self.result = False
        self.stop()

    async def prompt(self, ctx: commands.Context):
        await self.start(ctx, wait=True)

        if self.result is None:
            await ctx.reply('Você demorou muito para responder.')

        return self.result


class PunishmentMenu(_MenuBase):
    def __init__(self):
        super().__init__(delete_message_after=True)

        self.reason = None
        self._reasons = [
            'Violação das Diretrizes do Discord',
            'Má convivência',
            'Conteúdo NSFW',
            'Flood/Spam',
            'Divulgação',
            'Desrespeito aos tópicos',
            'Poluição sonora'
        ]

        for i in range(1, len(self._reasons) + 1):
            emoji = f'{i}\N{variation selector-16}\N{combining enclosing keycap}'
            button = menus.Button(emoji, self.on_reason)

            self.add_button(button)

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
        reasons = []
        for i, reason in enumerate(self._reasons, start=1):
            emoji = f'{i}\N{variation selector-16}\N{combining enclosing keycap}'
            reasons.append(f'{emoji} - {reason}')

        return await ctx.reply('\n'.join(reasons))

    async def on_reason(self, payload: discord.RawReactionActionEvent):
        index = int(str(payload.emoji)[0]) - 1
        self.reason = self._reasons[index]
        self.stop()

    async def prompt(self, ctx: commands.Context):
        await self.start(ctx, wait=True)
        return self.reason


class ListPaginator(menus.ListPageSource):
    def __init__(self, data, per_page: int = 8):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu: _MenuBase, entries):
        footer = {
            'text': f'Página {menu.current_page + 1}/{self.get_max_pages()}'}
        return menu.ctx.get_embed('\n'.join(entries), footer=footer)


class FieldPaginator(menus.ListPageSource):
    def __init__(self, data, per_page: int = 8):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu: _MenuBase, entries):
        footer = {
            'text': f'Página {menu.current_page + 1}/{self.get_max_pages()}'}
        return menu.ctx.get_embed(fields=entries, footer=footer)


class Menu(_MenuPagesBase):
    def __init__(self, data, *, paginator_type: int = 0, per_page: int = 8):
        _types = [ListPaginator, FieldPaginator]
        super().__init__(
            _types[paginator_type](
                data,
                per_page=per_page),
            delete_message_after=True)


class HelpPaginator(menus.ListPageSource):
    def __init__(self, commands: Mapping[commands.Cog, List[commands.Command]]):
        entries = sorted(commands.keys(), key=lambda c: c.qualified_name)
        self.commands = commands

        super().__init__(entries, per_page=6)

    def get_opening_note(self, ctx: commands.Context) -> str:
        command = f'{ctx.prefix}{ctx.invoked_with}'
        return 'Use `{0} [comando]` para mais informações sobre um comando.\n' \
               'Use `{0} [categoria]` para mais informações sobre uma categoria.'.format(command)

    async def format_page(self, menu: _MenuBase, cogs: List[commands.Cog]):
        ctx = menu.ctx

        embed = discord.Embed(description=self.get_opening_note(ctx), color=ctx.bot.color)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.set_footer(text=f'Página {menu.current_page + 1}/{self.get_max_pages()}')

        fields = []
        for cog in cogs:
            commands = [f'`{cmd.qualified_name}`' for cmd in self.commands.get(cog)]
            embed.add_field(name=cog.qualified_name, value=', '.join(commands), inline=False)

        return embed


class HelpMenu(_MenuPagesBase):
    def __init__(self, data):
        super().__init__(HelpPaginator(data), clear_reactions_after=True)
