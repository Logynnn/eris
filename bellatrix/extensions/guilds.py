from typing import Optional

import asyncpg
import discord
from discord.ext import commands

from utils import database
from utils.menus import Menu
from utils import checks


GUILD_SEPARATOR_ROLE_ID = 804026477745143808


class GuildsTable(database.Table, table_name='guilds'):
    id = database.PrimaryKeyColumn()
    name = database.Column(database.String, index=True, unique=True)
    icon_url = database.Column(database.String, nullable=True)
    created_at = database.Column(database.Datetime)
    role_id = database.Column(database.Integer(big=True), unique=True)
    owner_id = database.Column(database.Integer(big=True), unique=True)


class GuildMembers(database.Table, table_name='guild_members'):
    user_id = database.Column(database.Integer(big=True), primary_key=True)
    guild_id = database.Column(database.ForeignKey('guilds', 'id'), index=True)


class Guild:
    def __init__(self, ctx: commands.Context, *, record: asyncpg.Record):
        self._ctx = ctx

        self.id = record['id']
        self.name = record['name']
        self.icon_url = record['icon_url']
        self.created_at = record['created_at']

        self.role = ctx.guild.get_role(record['role_id'])

        owner_id = record['owner_id']
        members = record['members']

        get_member = ctx.guild.get_member

        self.owner = get_member(owner_id)
        self.members = [get_member(user_id)
                        for user_id in members if user_id != owner_id]

    async def delete(self, forced: bool = False):
        term = 'esta' if forced else 'sua'

        result = await self._ctx.prompt(f'Você realmente deseja deletar {term} guilda?')
        if not result:
            return

        query = '''
            DELETE FROM guilds
            WHERE id = $1
        '''

        await self._ctx.bot.manager.execute(query, self.id)
        await self.role.delete(reason=f'Deletando cargo da guilda "{self.name}".')

        await self._ctx.reply(f'Você deletou a guilda `{self.name}`.')

    def __repr__(self):
        return '<Guild id={0.id} name={0.name!r}>'.format(self)


class GuildConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        query = '''
            WITH guild_members AS (
                SELECT guild_id, array_agg(user_id) AS members
                FROM guild_members
                GROUP BY guild_id
            )
            SELECT id, name, icon_url, created_at, role_id, owner_id, members FROM guilds, guild_members
            WHERE guild_id = id AND name = $1
        '''
        record = await ctx.bot.manager.fetch_row(query, argument)
        return Guild(ctx, record=record) if record else None


class Guilds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def separator_role(self) -> discord.Role:
        return self.bot.cosmic.get_role(GUILD_SEPARATOR_ROLE_ID)

    async def has_guild(self, user_id: int) -> bool:
        query = 'SELECT * FROM guild_members WHERE user_id = $1'
        fetch = await self.bot.manager.fetch_row(query, user_id)
        return bool(fetch)

    async def get_guild(self, ctx: commands.Context, user_id: int) -> Optional[Guild]:
        query = '''
            WITH guild_members AS (
                SELECT guild_id, array_agg(user_id) AS members
                FROM guild_members
                GROUP BY guild_id
            )
            SELECT id, name, icon_url, created_at, role_id, owner_id, members FROM guilds, guild_members
            WHERE guild_id = id AND $1 = ANY(members)
        '''
        record = await ctx.bot.manager.fetch_row(query, user_id)
        return Guild(ctx, record=record) if record else None

    @commands.group(invoke_without_command=True)
    async def guild(self, ctx: commands.Context, *, guild: GuildConverter = None):
        await self.guild_info(ctx, guild=guild)

    @guild.command(name='create')
    @checks.is_premium()
    async def guild_create(self, ctx: commands.Context, *, name: str):
        if len(name) > 25:
            return await ctx.reply('Esse nome é muito longo. Escolha um nome menor.')

        if await self.has_guild(ctx.author.id):
            return await ctx.reply('Você já possui uma guilda.')

        role = await ctx.guild.create_role(name=name, reason=f'Criação da guilda "{name}".')
        await ctx.author.add_roles(role)

        all_roles = ctx.guild.roles[1:]
        all_roles.insert(all_roles.index(self.separator_role), role)

        positions = {
            role: index for index,
            role in enumerate(
                all_roles,
                start=1)}
        await ctx.guild.edit_role_positions(positions=positions, reason='Consertando as posições dos cargos.')

        query = '''
            WITH to_insert AS (
                INSERT INTO guilds AS entries (name, created_at, role_id, owner_id)
                VALUES ($1, $2, $3, $4)
                RETURNING entries.id
            )
            INSERT INTO guild_members (user_id, guild_id)
            SELECT $4, entry.id
            FROM (
                SELECT id FROM to_insert
                UNION ALL
                SELECT id FROM guilds WHERE name = $1
                LIMIT 1
            ) AS entry
        '''
        try:
            await self.bot.manager.execute(query, name, ctx.message.created_at, role.id, ctx.author.id)
        except asyncpg.UniqueViolationError:
            return await ctx.reply('Já existe uma guilda com este nome.')

        await ctx.reply(f'Você criou a guilda `{name}`.')

    @guild.command(name='delete', aliases=['del'])
    async def guild_delete(self, ctx: commands.Context):
        guild = await self.get_guild(ctx, ctx.author.id)
        if not guild:
            return await ctx.reply('Você não possui uma guilda.')

        if guild.owner.id != ctx.author.id:
            return await ctx.reply('Você não é o dono dessa guilda.')

        await guild.delete()

    @guild.command(name='forcedelete', aliases=['fdelete', 'fdel'])
    @checks.is_staffer()
    async def guild_forcedelete(self, ctx: commands.Context, *, guild: GuildConverter):
        if not guild:
            return await ctx.reply('Guilda não encontrada.')

        await guild.delete(forced=True)

    @guild.command(name='icon')
    async def guild_icon(self, ctx: commands.Context, url: str):
        guild = await self.get_guild(ctx, ctx.author.id)
        if not guild:
            return await ctx.reply('Você não possui uma guilda.')

        if guild.owner.id != ctx.author.id:
            return await ctx.reply('Você não é o dono desta guilda.')

        match = self.bot._image_url_regex.match(url)
        if not match or not match.group(0):
            return await ctx.reply('Esta é uma URL inválida.')

        query = '''
            UPDATE guilds
            SET icon_url = $2
            WHERE owner_id = $1
        '''
        await self.bot.manager.execute(query, ctx.author.id, url)

        await ctx.reply('Seu nome ícone de guilda foi alterado.', image=url)

    @guild.command(name='name')
    async def guild_name(self, ctx: commands.Context, *, name: str):
        guild = await self.get_guild(ctx, ctx.author.id)
        if not guild:
            return await ctx.reply('Você não possui uma guilda.')

        if guild.owner.id != ctx.author.id:
            return await ctx.reply('Você não é o dono dessa guilda.')

        if len(name) > 25:
            return await ctx.reply('Esse nome é muito longo. Escolha um nome menor.')

        query = '''
            UPDATE guilds
            SET name = $2
            WHERE owner_id = $1
        '''
        try:
            await self.bot.manager.execute(query, ctx.author.id, name)
        except asyncpg.UniqueViolationError:
            return await ctx.reply('Já existe uma guilda com este nome.')

        await guild.role.edit(name=name, reason=f'Mudando o nome da guilda para "{name}".')
        await ctx.reply(f'Você alterou o nome da guilda para `{name}`.')

    @guild.command(name='color', aliases=['colour'])
    async def guild_color(self, ctx: commands.Context, color: discord.Color):
        guild = await self.get_guild(ctx, ctx.author.id)
        if not guild:
            return await ctx.reply('Você não possui uma guilda.')

        if guild.owner.id != ctx.author.id:
            return await ctx.reply('Você não é o dono dessa guilda.')

        hex_color = '#' + format(color.value, '06X').lower()
        reason = f'Mudando a cor da guilda "{guild.name}" para {hex_color}'

        await guild.role.edit(color=color, reason=reason)
        await ctx.reply(f'Você alterou a cor da sua guilda para `{hex_color}`', color=color.value)

    @guild.command(name='info')
    async def guild_info(self, ctx: commands.Context, *, guild: GuildConverter = None):
        guild = guild or await self.get_guild(ctx, ctx.author.id)

        if not guild:
            return await ctx.reply('Guilda não encontrada.')

        footer = {'text': f'ID: {guild.id}'}

        title = guild.name
        owner = guild.owner
        thumbnail = guild.icon_url
        color = guild.role.color.value

        fields = []

        mentions = [member.mention for member in guild.members]
        members = ', '.join(mentions) or 'Não há membros nessa guilda.'

        fields.append(
            {'name': 'Dono', 'value': owner.mention, 'inline': False})
        fields.append(
            {'name': f'Membros [{len(mentions)}]', 'value': members, 'inline': False})

        await ctx.reply(
            title=title,
            fields=fields,
            thumbnail=thumbnail,
            footer=footer,
            color=color
        )

    @guild.command(name='list')
    async def guild_list(self, ctx: commands.Context):
        query = '''
            SELECT * FROM guilds
            ORDER BY id
        '''
        fetch = await self.bot.manager.fetch(query)

        data = []
        for record in fetch:
            name = record['name']
            guild_id = record['id']

            data.append(f'**{name}** (ID: `{guild_id}`)')

        menu = Menu(data)
        await menu.start(ctx)

    @commands.command()
    async def guilds(self, ctx: commands.Context):
        await self.guild_list(ctx)


def setup(bot: commands.Bot):
    bot.add_cog(Guilds(bot))
