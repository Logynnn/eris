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

import asyncio
from typing import Optional

import asyncpg
import aiohttp
import aioredis
import discord
from discord.ext import commands


GREEN_TICK_EMOJI = '<:GreenTick:821520856701337611>'
RED_TICK_EMOJI   = '<:RedTick:821520905968418836>'
GREY_TICK_EMOJI  = '<:GreyTick:821520843334615050>'


class ErisContext(commands.Context):
    @property
    def pool(self) -> asyncpg.Pool:
        return self.bot.pool

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    @property
    def cache(self) -> aioredis.Redis:
        return self.bot.cache

    def tick(self, value: Optional[bool]) -> str:
        '''Retorna um emoji para um valor booleano ou nulo.

        Parameters
        ----------
        value: Optional[:class:`bool`]
            O valor a ser "traduzido".

        Returns
        -------
        :class:`str`
            O emoji correspondente ao valor.
        '''        
        emojis = {
            True: GREEN_TICK_EMOJI,
            False: RED_TICK_EMOJI,
            None: GREEN_TICK_EMOJI
        }

        return emojis[value]

    def progress_bar(self, amount: int, *, length: int = 20) -> str:
        '''Cria uma barra de progresso.

        Parameters
        ----------
        amount: :class:`int`
            A porcentagem na qual a barra deve ser preenchida.

        Returns
        -------
        :class:`str`
            A barra de progresso.
        '''        
        full_char = '█'
        empty_char = '·'

        full = round(int(amount) / (100 / length))
        return f'`[{(full_char * full):{empty_char}<{length}}]`'

    def get_percentage(self, amount: int, total: int) -> int:
        '''Retorna uma porcentagem dado um valor e o total.

        Parameters
        ----------
        amount: :class:`int`
            O valor base para ser usado.
        total: :class:`int`
            O total base para ser usado.

        Returns
        -------
        :class:`int`
            A porcentagem relacional dos valores dado.
        '''        
        return (amount * 100) / total

    def get_embed(self, content: str = None, **kwargs) -> discord.Embed:
        '''Gera uma :class:`discord.Embed` pronta para ser usada.

        Parameters
        ----------
        content: :class:`str`
            O conteúdo a ser usado na :class:`discord.Embed`.

        Returns
        -------
        :class:`discord.Embed`
            A :class:`discord.Embed` pronta para ser usada.
        '''        
        author = self.author

        title = kwargs.get('title')

        embed = discord.Embed(title=title, description=content, colour=0x2f3136)
        embed.set_author(name=author.display_name, icon_url=author.avatar_url)
        return embed

    async def reply(self, content: str, **kwargs) -> discord.Message:
        '''Responde um usuário.

        Parameters
        ----------
        content: :class:`str`
            O conteúdo da mensagem.

        Returns
        -------
        :class:`discord.Message`
            A mensagem enviada.
        '''
        title = kwargs.pop('title', None)
        embed = kwargs.pop('embed', self.get_embed(content, title=title))
        return await super().reply(embed=embed, mention_author=False)
