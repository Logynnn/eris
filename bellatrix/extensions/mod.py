import typing

import discord
import humanize
from discord.ext import commands

from utils import database
from utils.menus import PunishmentMenu
from utils.embed import Embed
from utils.time import FutureTime
from .reminder import Timer


LOG_CHANNEL_ID = 798013309617176587
MUTE_ROLE_ID = 799064942048444437

class PunishmentImage(database.Table, table_name='punishment_images'):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    url = database.Column(database.String())

class Mod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cosmic = bot.cosmic

        self.log_channel = bot.cosmic.get_channel(LOG_CHANNEL_ID)
        self.mute_role = bot.cosmic.get_role(MUTE_ROLE_ID)

    async def get_punishment_image(self, member: discord.Member):
        query = 'SELECT url FROM punishment_images WHERE user_id = $1'
        fetch = await self.bot.manager.fetch_row(query, member.id)
        
        if not fetch:
            return None

        return fetch[0]

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
    @commands.has_permissions(kick_members=True)
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

        await member.add_roles(self.mute_role, reason=f'Ação realizada por {ctx.author} (ID: {ctx.author.id}')
        timer = await reminder.create_timer(
            when.datetime,
            'mute',
            ctx.author.id,
            member.id,
            created=ctx.message.created_at
        )

        image = await self.get_punishment_image(ctx.author)
        delta = humanize.precisedelta(when.datetime - ctx.message.created_at, format='%0.0f')

        await ctx.reply(title=f'{member} foi silenciado por {delta}', image=image)
        self.bot.dispatch('moderation_command', 'mute', ctx, member, duration=delta)

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
            await member.remove_roles(self.mute_role, reason=reason)
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

        term = terms[name]
        duration = kwargs.get('duration', None)

        embed = Embed(
            title=f'Usuário {term}',
            thumbnail=member.avatar_url,
            author={'name': str(ctx.author), 'icon_url': ctx.author.avatar_url},
            color=self.cosmic.me.color
        )

        embed.add_field(name='Usuário', value=str(member), inline=False)
        embed.add_field(name='ID', value=f'`{member.id}`', inline=False)
        embed.add_field(name='Motivo', value=reason, inline=False)

        if duration:
            embed.add_field(name='Duração', value=duration, inline=False)

        await self.log_channel.send(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(Mod(bot))