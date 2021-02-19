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

import re

import discord
import asyncpg
from discord.ext import commands, tasks


from utils import database


# TODO: Adicionar uma documentação decente.

THRESHOLD = 4
STARBOARD_CHANNEL_ID = 797633732340219964


class StarError(commands.CheckFailure):
    pass


class StarboardEntry(database.Table, table_name='starboard_entries'):
    id = database.PrimaryKeyColumn()

    bot_message_id = database.Column(
        database.Integer(
            big=True),
        index=True,
        nullable=True)
    message_id = database.Column(
        database.Integer(
            big=True),
        index=True,
        unique=True)
    channel_id = database.Column(database.Integer(big=True))
    author_id = database.Column(database.Integer(big=True))


class Starrers(database.Table):
    id = database.PrimaryKeyColumn()

    author_id = database.Column(database.Integer(big=True))
    entry_id = database.Column(
        database.ForeignKey(
            'starboard_entries',
            'id'),
        index=True)

    @classmethod
    def create_table(cls, *, exists_ok=True):
        statement = super().create_table(exists_ok=exists_ok)
        sql = 'CREATE UNIQUE INDEX IF NOT EXISTS starrers_uniq_idx ON starrers (author_id, entry_id)'
        return statement + '\n' + sql


class Starboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.cosmic = bot.cosmic
        self.starboard = bot.cosmic.get_channel(STARBOARD_CHANNEL_ID)

        self.spoilers = re.compile(r'\|\|(.+?)\|\|')

        self._message_cache = {}
        self.clean_message_cache.start()

    def cog_unload(self):
        self.clean_message_cache.cancel()

    @tasks.loop(hours=1)
    async def clean_message_cache(self):
        self._message_cache.clear()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.reaction_action('star', payload)

    @commands.Cog.listener()
    async def on_raw_reaction_delete(self, payload: discord.RawReactionActionEvent):
        await self.reaction_action('unstar', payload)

    async def reaction_action(self, fmt: str, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != '⭐':
            return

        channel = self.cosmic.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        method = getattr(self, f'{fmt}_message')

        user = payload.member or (await self.get_or_fetch_member(self.cosmic, payload.user_id))
        if user is None or user.bot:
            return

        try:
            await method(channel, payload.message_id, payload.user_id)
        except StarError:
            pass

    async def get_or_fetch_member(self, guild: discord.Guild, member_id: int):
        member = guild.get_member(member_id)
        if member is not None:
            return member

        try:
            return await guild.fetch_member(member_id)
        except discord.HTTPException:
            return None

    async def star_message(self, channel: discord.TextChannel, message_id: int, starrer_id: int):
        message = await self.get_message(channel, message_id)

        if message is None:
            raise StarError('Message not found')

        if message.author.id == starrer_id:
            raise StarError('You cannot star your own message')

        if (len(message.content) == 0 and len(message.attachments)
                == 0) or message.type is not discord.MessageType.default:
            raise StarError('This message cannot be starred')

        query = '''
            WITH to_insert AS (
                INSERT INTO starboard_entries AS entries (message_id, channel_id, author_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (message_id) DO NOTHING
                RETURNING entries.id
            )
            INSERT INTO starrers (author_id, entry_id)
            SELECT $4, entry.id
            FROM (
                SELECT id FROM to_insert
                UNION ALL
                SELECT id FROM starboard_entries WHERE message_id = $1
                LIMIT 1
            ) AS entry
            RETURNING entry_id;
        '''

        try:
            record = await self.bot.manager.fetch_row(query, message_id, channel.id, message.author.id, starrer_id)
        except asyncpg.UniqueViolationError:
            raise StarError('You already starred this message')

        entry_id = record[0]

        query = 'SELECT COUNT(*) FROM starrers WHERE entry_id = $1'
        record = await self.bot.manager.fetch_row(query, entry_id)

        count = record[0]
        if count < THRESHOLD:
            return

        content, embed = self.get_content(message, count)

        query = 'SELECT bot_message_id FROM starboard_entries WHERE message_id = $1'
        record = await self.bot.manager.fetch_row(query, message_id)
        bot_message_id = record[0]

        if bot_message_id is None:
            new_message = await self.starboard.send(content, embed=embed)
            query = 'UPDATE starboard_entries SET bot_message_id = $1 WHERE message_id = $2'
            await self.bot.manager.execute(query, new_message.id, message_id)
        else:
            new_message = await self.get_message(self.starboard, bot_message_id)
            if new_message is None:
                query = 'DELETE FROM starboard_entries WHERE message_id = $1'
                await self.bot.manager.exeucte(query, message_id)
            else:
                await new_message.edit(content=content, embed=embed)

    async def unstar_message(self, channel: discord.TextChannel, message_id: int, starrer_id: int):
        query = '''
            DELETE FROM starrers USING starboard_entries entry
            WHERE entry.message_id = $1
            AND entry.id = starrers.entry_id
            AND starrers.author_id = $2
            RETURNING starrers.entry_id, entry.bot_message_id
        '''

        record = await self.bot.manager.fetch_row(query, message_id, starrer_id)
        if record is None:
            raise StarError('You have not starred this message')

        entry_id = record[0]
        bot_message_id = record[1]

        query = 'SELECT COUNT(*) FROM starrers WHERE entry_id = $1'
        count = await self.bot.manager.fetch_row(query, entry_id)
        count = count[0]

        if count == 0:
            query = 'DELETE FROM starboard_entries WHERE id = $1'
            await self.bot.manager.execute(query, entry_id)

        if bot_message_id is None:
            return

        bot_message = await self.get_message(self.starboard, bot_message_id)
        if bot_message is None:
            return

        if count < THRESHOLD:
            if count:
                query = 'UPDATE starboard_entries SET bot_message_id = NULL WHERE id = $1'
                await self.bot.manager.execute(query, entry_id)

            await bot_message.delete()
        else:
            message = await self.get_message(channel, message_id)
            if message is None:
                raise StarError('Message not found')

            content, embed = await self.get_content(message, count)
            await bot_message.edit(content=content, embed=embed)

    async def get_message(self, channel: discord.TextChannel, message_id: int) -> discord.Message:
        try:
            return self._message_cache[message_id]
        except KeyError:
            try:
                o = discord.Object(id=message_id + 1)
                message = await channel.history(limit=1, before=o).next()

                if message.id != message_id:
                    return None

                self._message_cache[message_id] = message
                return message
            except Exception:
                return None

    def get_content(self, message: discord.Message, stars: int):
        if stars:
            content = f'**{stars} 🌟** - {message.channel.mention}'
        else:
            content = f'🌟 - {message.channel.mention}'

        embed = discord.Embed(description=message.content, colour=0xffff5c)

        if message.embeds:
            data = message.embeds[0]
            if data.type == 'image' and not self.is_url_spoiler(
                    message.content, data.url):
                embed.set_image(url=data.url)

        if message.attachments:
            file = message.attachments[0]
            spoiler = file.is_spoiler()

            if not spoiler and file.url.lower().endswith(
                    ('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=file.url)
            elif spoiler:
                embed.add_field(
                    name='Anexo',
                    value=f'||[{file.filename}]({file.url})||',
                    inline=False)
            else:
                embed.add_field(
                    name='Anexo',
                    value=f'[{file.filename}]({file.url})',
                    inline=False)

        embed.add_field(name='Mensagem original',
                        value=f'[Clique aqui]({message.jump_url})')
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar_url_as(
                format='png'))

        return content, embed

    def is_url_spoiler(self, text: str, url: str):
        spoilers = self.spoilers.findall(text)
        for spoiler in spoilers:
            if url in spoiler:
                return True
        return False


def setup(bot: commands.Bot):
    bot.add_cog(Starboard(bot))
