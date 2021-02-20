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

import typing
import re
import json

import discord
import humanize
from discord.ext import commands, flags
from jishaku.codeblocks import codeblock_converter

from utils import database
from utils.menus import PunishmentMenu
from utils.embed import Embed
from utils.time import FutureTime
from .reminder import Timer


class PunishmentImage(database.Table, table_name='punishment_images'):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    url = database.Column(database.String())


class Mod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cosmic = bot.cosmic

    async def get_punishment_image(self, member: discord.Member):
        query = 'SELECT url FROM punishment_images WHERE user_id = $1'
        fetch = await self.bot.manager.fetch_row(query, member.id)

        if not fetch:
            return None

        return fetch[0]

    @commands.group()
    async def config(self, ctx: commands.Context):
        pass

    @config.command()
    async def image(self, ctx: commands.Context, url: str):
        match = self.bot._image_url_regex.match(url)
        if not match or not match.group(0):
            return await ctx.reply('Este é um link inválido.')

        query = '''
            INSERT INTO punishment_images (user_id, url)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET url = $2
        '''
        await self.bot.manager.execute(query, ctx.author.id, url)

        await ctx.reply('Você mudou sua imagem de banimento com sucesso.')

    @commands.command(aliases=['b'])
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, *, member: discord.Member):
        image = await self.get_punishment_image(ctx.author)

        try:
            await member.ban(reason=f'Ação realizada por {ctx.author} (ID: {ctx.author.id})')
        except discord.Forbidden:
            await ctx.reply('Não foi possível banir este usuário.')
        else:
            await ctx.reply(title=f'{member} foi banido com sucesso', image=image)
            self.bot.dispatch('moderation_command', 'ban', ctx, member)

    @commands.command(aliases=['k'])
    @commands.has_guild_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, *, member: discord.Member):
        image = await self.get_punishment_image(ctx.author)

        try:
            await member.kick(reason=f'Ação realizada por {ctx.author} (ID: {ctx.author.id})')
        except discord.Forbidden:
            await ctx.reply('Não foi possível expulsar este usuário.')
        else:
            await ctx.reply(title=f'{member} foi expulso com sucesso', image=image)
            self.bot.dispatch('moderation_command', 'kick', ctx, member)

    @commands.command(aliases=['m'])
    @commands.has_guild_permissions(mute_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, *, when: FutureTime):
        reminder = ctx.bot.get_cog('Reminder')
        if not reminder:
            return await ctx.reply('Serviço indisponível, tente novamente mais tarde.')

        if self.bot.staff_role in member.roles:
            return await ctx.reply('Não foi possível silenciar este usuário.')

        await member.add_roles(self.bot.mute_role, reason=f'Ação realizada por {ctx.author} (ID: {ctx.author.id}')
        timer = await reminder.create_timer(
            when.datetime,
            'mute',
            ctx.author.id,
            member.id,
            created=ctx.message.created_at
        )

        image = await self.get_punishment_image(ctx.author)
        delta = humanize.precisedelta(
            when.datetime -
            ctx.message.created_at,
            format='%0.0f')

        await ctx.reply(title=f'{member} foi silenciado por {delta}', image=image)
        self.bot.dispatch(
            'moderation_command',
            'mute',
            ctx,
            member,
            duration=delta)

    @flags.command(aliases=['purge'])
    @flags.add_flag('--user', type=discord.User, nargs='+')
    @flags.add_flag('--contains', type=str, nargs='+')
    @flags.add_flag('--starts', type=str, nargs='+')
    @flags.add_flag('--ends', type=str, nargs='+')
    @flags.add_flag('--emoji', action='store_true')
    @flags.add_flag('--bot', action='store_const',
                    const=lambda m: m.author.bot)
    @flags.add_flag('--embeds', action='store_const',
                    const=lambda m: len(m.embeds))
    @flags.add_flag('--files', action='store_const',
                    const=lambda m: len(m.attachments))
    @flags.add_flag('--reactions', action='store_const',
                    const=lambda m: len(m.reactions))
    @flags.add_flag('--after', type=int)
    @flags.add_flag('--before', type=int)
    @commands.has_guild_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 100, **flags):
        predicates = []
        amount = max(0, min(2000, amount))

        if flags['user']:
            predicates.append(lambda m: m.author in flags['user'])

        if flags['contains']:
            predicates.append(
                lambda m: any(
                    sub in m.content for sub in flags['contains']))

        if flags['starts']:
            predicates.append(lambda m: any(m.content.startswith(s)
                                            for s in flags['starts']))

        if flags['ends']:
            predicates.append(lambda m: any(m.content.endswith(s)
                                            for s in flags['ends']))

        if flags['emoji']:
            predicates.append(
                lambda m: self.bot._emoji_regex.search(
                    m.content))

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
        await ctx.reply(f'Removi `{len(deleted)}` mensagens com sucesso.')

    @commands.command()
    async def embed(self, ctx: commands.Context, *, code: codeblock_converter):
        code = code.content.replace('{color}', str(ctx.bot.color))
        embed = Embed.from_dict(json.loads(code))

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_mute_complete(self, timer: Timer):
        moderator_id, member_id = timer.args
        await self.bot.wait_until_ready()

        member = self.cosmic.get_member(member_id)
        moderator = self.cosmic.get_member(moderator_id)

        if not member:
            return

        reason = f'Removendo silenciamento realizado por {moderator}'

        try:
            await member.remove_roles(self.bot.mute_role, reason=reason)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_moderation_command(self, name: str, ctx: commands.Context, member: discord.Member, **kwargs):
        terms = {
            'ban': 'banido',
            'kick': 'expulso',
            'mute': 'silenciado'
        }

        menu = PunishmentMenu()
        reason = await menu.prompt(ctx)

        channel = self.bot.log_channel

        term = terms[name]
        duration = kwargs.get('duration', None)

        embed = Embed(
            title=f'Usuário {term}',
            thumbnail=member.avatar_url,
            author={'name': str(ctx.author),
                    'icon_url': ctx.author.avatar_url},
            color=ctx.bot.color
        )

        embed.add_field(name='Usuário', value=str(member), inline=False)
        embed.add_field(name='ID', value=f'`{member.id}`', inline=False)
        embed.add_field(name='Motivo', value=reason, inline=False)

        if duration:
            embed.add_field(name='Duração', value=duration, inline=False)

        await channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Mod(bot))
