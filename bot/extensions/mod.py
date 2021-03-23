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
import asyncio
from typing import Optional

import discord
from discord.ext import commands, flags
from discord.ext.menus import Button

from eris import Eris
from utils.context import ErisContext
from utils.menus import MenuBase
from utils.time import FutureTime


PUNISHMENTS_CHANNEL_ID = 798013309617176587


class ReasonMenu(MenuBase):
    '''Menu para selecionar o motivo da punição.'''

    def __init__(self):
        super().__init__(delete_message_after=True)

        # Por padrão, será "Má convivência".
        # Caso o autor não responda o menu, será usado
        # este valor padrão.
        self.reason = 'Má convivência'

        # Todos os motivos para banir um usuário.
        self.all_reasons = [
            'Violação das Diretrizes do Discord',
            'Má convivência',
            'Conteúdo NSFW',
            'Flood/Spam',
            'Divulgação',
            'Desrespeito aos tópicos',
            'Poluição sonora'
        ]

        for i in range(1, len(self.all_reasons) + 1):
            emoji = f'{i}\N{variation selector-16}\N{combining enclosing keycap}'
            self.add_button(Button(emoji, self.on_reason))

    async def send_initial_message(self, ctx: ErisContext, channel: discord.TextChannel):
        reasons = []

        for i, reason in enumerate(self.all_reasons, start=1):
            emoji = f'{i}\N{variation selector-16}\N{combining enclosing keycap}'
            reasons.append(f'{emoji} - {reason}')

        return await ctx.reply('\n'.join(reasons))

    async def on_reason(self, payload: discord.RawReactionActionEvent):
        self.reason = self.all_reasons[int(str(payload.emoji)[0]) - 1]
        self.stop()

    async def prompt(self, ctx: ErisContext):
        await self.start(ctx, wait=True)
        return self.reason


class PunishmentType(enum.Enum):
    BANNED = 'banido'
    KICKED = 'expulso'
    MUTED  = 'silenciado'


class Mod(commands.Cog, name='Moderação'):
    '''Comandos relacionados a moderação do servidor.'''

    def __init__(self, bot: Eris):
        self.bot = bot

    def cog_check(self, ctx: ErisContext):
        # Somente staffers usarão os comandos deste cog.
        return ctx.bot.staff_role in ctx.author.roles

    @commands.Cog.listener()
    async def on_first_launch(self):
        self.log = self.bot.cosmic.get_channel(PUNISHMENTS_CHANNEL_ID)

    # TODO: Hackban.
    # TODO: Banir mais de uma pessoa de uma vez.
    @flags.command(aliases=['b'])
    @flags.add_flag('--quiet', '-q', action='store_true')
    async def ban(self, ctx: ErisContext, member: discord.Member, **flags):
        quiet = flags['quiet']

        try:
            await member.ban(reason=f'Ação realizada por {ctx.author} (ID: {ctx.author.id})')
        except discord.Forbidden:
            await ctx.reply('Não foi possível banir este usuário.')
        else:
            await ctx.reply(f'Eita, `{member}` foi banido do servidor.')

            if not quiet:
                self.bot.dispatch('punishment', ctx, member, PunishmentType.BANNED)

    @flags.command(aliases=['k'])
    @flags.add_flag('--quiet', '-q', action='store_true')
    async def kick(self, ctx: ErisContext, member: discord.Member, **flags):
        quiet = flags['quiet']

        try:
            await member.kick(reason=f'Ação realizada por {ctx.author} (ID: {ctx.author.id})')
        except discord.Forbidden:
            await ctx.reply('Não foi possível banir este usuário.')
        else:
            await ctx.reply(f'Eita, {member} foi expulso do servidor.')

            if not quiet:
                self.bot.dispatch('punishment', ctx, member, PunishmentType.KICKED)

    @flags.command(aliases=['c'])
    @flags.add_flag('--user', type=discord.User, nargs='+')
    @flags.add_flag('--contains', type=str, nargs='+')
    @flags.add_flag('--starts', type=str, nargs='+')
    @flags.add_flag('--ends', type=str, nargs='+')
    @flags.add_flag('--emoji', action='store_true')
    @flags.add_flag('--bot', action='store_const', const=lambda m: m.author.bot)
    @flags.add_flag('--embeds', action='store_const', const=lambda m: len(m.embeds))
    @flags.add_flag('--files', action='store_const', const=lambda m: len(m.attachments))
    @flags.add_flag('--reactions', action='store_const', const=lambda m: len(m.reactions))
    @flags.add_flag('--after', type=int)
    @flags.add_flag('--before', type=int)
    async def clear(self, ctx: ErisContext, amount: Optional[int] = 100, **flags):
        predicates = []
        amount = max(0, min(2000, amount))

        if flags['user']:
            predicates.append(lambda m: m.author in flags['user'])

        if flags['contains']:
            pred = lambda m: any(sub in m.content for sub in flags['contains'])
            predicates.append(pred)

        if flags['starts']:
            pred = lambda m: any(m.content.startswith(s) for s in flags['starts'])
            predicates.append(pred)

        if flags['ends']:
            pred = lambda m: any(m.content.endswith(s) for s in flags['ends'])
            predicates.append(pred)

        if flags['emoji']:
            pred = lambda m: self.bot._emoji_regex.search(m.content)
            predicates.append(pred)

        if flags['bot']:
            predicates.append(flags['bot'])

        if flags['embeds']:
            predicates.append(flags['embeds'])

        if flags['files']:
            predicates.append(flags['files'])

        if flags['reactions']:
            predicates.append(flags['reactions'])

        if flags['before']:
            before = discord.Object(id=flags['before'])
        else:
            before = ctx.message

        if flags['after']:
            after = discord.Object(id=flags['after'])
        else:
            after = None

        def predicate(m: discord.Message) -> bool:
            return all(pred(m) for pred in predicates)

        deleted = await ctx.channel.purge(limit=amount, before=before, after=after, check=predicate)
        message = await ctx.reply(f'Deletei `{len(deleted)}` mensagens deste canal.')

        # Esperar 5 segundos antes de deletar as mensagens
        await asyncio.sleep(5)
        await ctx.channel.delete_messages([*deleted, message])

    @commands.Cog.listener()
    async def on_punishment(self, ctx: ErisContext, member: discord.Member, punishment_type: PunishmentType, **kwargs):
        menu = ReasonMenu()
        reason = await menu.prompt(ctx)

        word = punishment_type.value
        duration = kwargs.get('duration')

        embed = discord.Embed(title=f'Usuário {word}', colour=0x2f3136)

        embed.set_thumbnail(url=member.avatar_url)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

        embed.add_field(name='Usuário', value=str(member), inline=False)
        embed.add_field(name='ID', value=f'`{member.id}`', inline=False)
        embed.add_field(name='Motivo', value=reason, inline=False)

        await self.log.send(embed=embed)



def setup(bot: Eris):
    bot.add_cog(Mod(bot))