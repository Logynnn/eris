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

from discord.ext import commands

from eris import Eris
from utils.context import ErisContext


NOTIFICATIONS_ROLE_ID = 815605411318202368


class Misc(commands.Cog, name='Miscelânea'):
    '''Comandos de miscelânea.'''

    def __init__(self, bot: Eris):
        self.bot = bot

    @commands.Cog.listener()
    async def on_first_launch(self):
        self.notifications_role = self.bot.cosmic.get_role(NOTIFICATIONS_ROLE_ID)

    @commands.command()
    async def notifications(self, ctx: ErisContext):
        '''
        Recebe (ou remove) o cargo de notificações.
        '''
        if self.notifications_role not in ctx.author.roles:
            method = ctx.author.add_roles
            word = 'recebeu'
        else:
            method = ctx.author.remove_roles
            word = 'removeu'

        reason = f'{word.title()} o cargo de notificações'
        await method(self.notifications_role, reason=reason)

        await ctx.reply(f'Você {word} o cargo de {self.notifications_role.mention}.')


def setup(bot: Eris):
    bot.add_cog(Misc(bot))
