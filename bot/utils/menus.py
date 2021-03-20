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
'''
This Source Code Form is subject to the
terms of the Mozilla Public License, v.
2.0. If a copy of the MPL was not
distributed with this file, You can
obtain one at
http://mozilla.org/MPL/2.0/.
'''

import enum
from typing import Any

import discord
from discord.ext import menus

from .context import ErisContext


DOUBLE_LEFT_EMOJI  = '<:DoubleLeft:821145728684261406>'
DOUBLE_RIGHT_EMOJI = '<:DoubleRight:821145747743178752>'
LEFT_EMOJI         = '<:Left:821145765212454913>'
RIGHT_EMOJI        = '<:Right:821145810128863252>'
STOP_EMOJI         = '<:Stop:821145785193725962>'


# Esse menu foi rebaseado para que ele remova
# a reação depois de um botão ser pressionado.
class MenuBase(menus.Menu):
    async def update(self, payload: discord.RawReactionActionEvent):
        if self._can_remove_reactions:
            if payload.event_type != 'REACTION_ADD':
                return

            await self.message.remove_reaction(payload.emoji, payload.member)
        await super().update(payload)


# Esse menu foi rebaseado para que ele remova
# a reação depois de um botão ser pressionado.
class MenuPagesBase(menus.MenuPages, inherit_buttons=False):
    async def update(self, payload: discord.RawReactionActionEvent):
        if self._can_remove_reactions:
            if payload.event_type != 'REACTION_ADD':
                return

            await self.message.remove_reaction(payload.emoji, payload.member)
        await super().update(payload)

    async def send_initial_message(self, ctx: ErisContext, channel: discord.TextChannel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await ctx.reply(**kwargs)

    async def show_page(self, page_number: int):
        page = await self._source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)

        mentions = discord.AllowedMentions(replied_user=False)
        await self.message.edit(**kwargs, allowed_mentions=mentions)

    def _skip_double_arrows(self) -> bool:
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages <= 2

    @menus.button(DOUBLE_LEFT_EMOJI, position=menus.First(0), skip_if=_skip_double_arrows)
    async def go_to_first_page(self, payload: discord.RawReactionActionEvent):
        '''Vai para a primeira página.'''
        await self.show_page(0)

    @menus.button(LEFT_EMOJI, position=menus.First(0))
    async def go_to_previous_page(self, payload: discord.RawReactionActionEvent):
        '''Vai para a página anterior.'''
        await self.show_checked_page(self.current_page - 1)
    
    @menus.button(STOP_EMOJI)
    async def stop_pages(self, payload: discord.RawReactionActionEvent):
        '''Para a sessão de paginamento.'''
        self.stop()

    @menus.button(RIGHT_EMOJI, position=menus.Last(0))
    async def go_to_next_page(self, payload: discord.RawReactionActionEvent):
        '''Vai para a próxima página.'''
        await self.show_checked_page(self.current_page + 1)

    @menus.button(DOUBLE_RIGHT_EMOJI, position=menus.Last(1), skip_if=_skip_double_arrows)
    async def go_to_last_page(self, payload: discord.RawReactionActionEvent):
        '''Vai para a última página.'''
        await self.show_page(self._source.get_max_pages() - 1)


class StringPageSource(menus.ListPageSource):
    '''Formata um menu baseado em um `list[:class:`str`]`.'''
    async def format_page(self, menu: MenuBase, entries: list[str]):
        footer = f'Página {menu.current_page + 1}/{self.get_max_pages()}'

        embed = menu.ctx.get_embed('\n'.join(entries))
        embed.set_footer(text=footer)
        return embed


class FieldPageSource(menus.ListPageSource):
    '''Formata um menu baseado em um `list[dict[:class:`str`, :class:`str`]]`.'''
    async def format_page(self, menu: MenuBase, entries: list[dict[str, str]]):
        footer = f'Página {menu.current_page + 1}/{self.get_max_pages()}'

        embed = menu.ctx.get_embed()
        embed.set_footer(text=footer)

        for field in entries:
            embed.add_field(**field)

        return embed


class SourceType(enum.Enum):
    STRING = StringPageSource
    FIELD  = FieldPageSource


class ErisMenuPages(MenuPagesBase):
    '''Cria um paginador interativo.

    Parameters
    ----------
    entries: list[:class:`typing.Any`]
        As entradas para serem paginadas.
    source: :class:`SourceType`
        O tipo de paginador a ser usado, por padrão é `SourceType.STRING`.
    per_page: :class:`int`
        Quantos elementos devem aparecer por página, por padrão é  `8`.

    Raises
    ------
    MenuError
        Caso a entrada não seja uma instância de `SourceType`.
    '''
    def __init__(self, entries: list[Any], *, source: SourceType = SourceType.STRING, per_page: int = 8):
        if not isinstance(source, SourceType):
            raise menus.MenuError('Source must be a subclass of SourceType')

        source = source.value(entries, per_page=per_page)
        super().__init__(source, clear_reactions_after=True)

    # async def send_initial_message(self, ctx: ErisContext, channel: discord.TextChannel):
    #     page = await self._source.get_page(0)
    #     kwargs = await self._get_kwargs_from_page(page)
    #     return await ctx.reply(**kwargs)

    # async def show_page(self, page_number: int):
    #     page = await self._source.get_page(page_number)
    #     self.current_page = page_number
    #     kwargs = await self._get_kwargs_from_page(page)

    #     mentions = discord.AllowedMentions(replied_user=False)
    #     await self.message.edit(**kwargs, allowed_mentions=mentions)

    # def _skip_double_arrows(self) -> bool:
    #     max_pages = self._source.get_max_pages()
    #     if max_pages is None:
    #         return True
    #     return max_pages <= 2

    # @menus.button(DOUBLE_LEFT_EMOJI, position=menus.First(0), skip_if=_skip_double_arrows)
    # async def go_to_first_page(self, payload: discord.RawReactionActionEvent):
    #     '''Vai para a primeira página.'''
    #     await self.show_page(0)

    # @menus.button(LEFT_EMOJI, position=menus.First(0))
    # async def go_to_previous_page(self, payload: discord.RawReactionActionEvent):
    #     '''Vai para a página anterior.'''
    #     await self.show_checked_page(self.current_page - 1)
    
    # @menus.button(STOP_EMOJI)
    # async def stop_pages(self, payload: discord.RawReactionActionEvent):
    #     '''Para a sessão de paginamento.'''
    #     self.stop()

    # @menus.button(RIGHT_EMOJI, position=menus.Last(0))
    # async def go_to_next_page(self, payload: discord.RawReactionActionEvent):
    #     '''Vai para a próxima página.'''
    #     await self.show_checked_page(self.current_page + 1)

    # @menus.button(DOUBLE_RIGHT_EMOJI, position=menus.Last(1), skip_if=_skip_double_arrows)
    # async def go_to_last_page(self, payload: discord.RawReactionActionEvent):
    #     '''Vai para a última página.'''
    #     await self.show_page(self._source.get_max_pages() - 1)
