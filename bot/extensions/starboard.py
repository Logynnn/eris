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

import datetime
import re
from typing import Optional

import discord
import asyncpg
from discord.ext import commands, tasks

from eris import Eris
from utils import database


STARBOARD_CHANNEL_ID = 797633732340219964

THRESHOLD = 4


class StarboardEntries(database.Table, table_name='starboard'):
    id = database.PrimaryKeyColumn()

    bot_message_id = database.Column(database.Integer(big=True), index=True, nullable=True)
    message_id = database.Column(database.Integer(big=True), index=True, unique=True)
    channel_id = database.Column(database.Integer(big=True))
    author_id = database.Column(database.Integer(big=True))


class Starrers(database.Table):
    id = database.PrimaryKeyColumn()

    author_id = database.Column(database.Integer(big=True))
    entry_id = database.Column(database.ForeignKey('starboard', 'id'), index=True)

    @classmethod
    def create_table(cls, *, exists_ok: bool = True) -> str:
        statement = super().create_table(exists_ok=exists_ok)
        sql = 'CREATE UNIQUE INDEX IF NOT EXISTS starrers_uniq_idx ON starrers (author_id, entry_id);'
        return statement + '\n' + sql


class StarError(Exception):
    pass


class Starboard(commands.Cog):
    '''Sistema de starboard para um sistema de upvote.

    Há duas maneiras de usar essa funcionalidade, a primeira é
    via reações, reaja uma mensagem com ⭐ e o bot vai automaticamente
    adicionar (ou remover) do starboard.

    A segunda é via comandos. Ative o Modo de Desenvolvedor para
    conseguir acessar o ID de uma mensagem e usar os comandos de
    star/unstar.
    '''

    def __init__(self, bot: Eris):
        self.bot = bot

        self.spoilers = re.compile(r'\|\|(.+?)\|\|')

        # Criar um cache simples de mensagens para
        # evitar fazer requests desnecessárias.
        self._message_cache = {}
        self.clean_message_cache.start()

    def cog_unload(self):
        self.clean_message_cache.cancel()

    @commands.Cog.listener()
    async def on_first_launch(self):
        self.starboard = self.bot.cosmic.get_channel(STARBOARD_CHANNEL_ID)

    @tasks.loop(hours=1)
    async def clean_message_cache(self):
        self._message_cache.clear()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.reaction_action('star', payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.reaction_action('unstar', payload)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        # Se uma mensagem do starboard for deletada então
        # podemos removê-la do banco de dados.
        sql = 'DELETE FROM starboard WHERE bot_message_id = $1;'
        await self.bot.pool.execute(sql, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        # Se uma das mensagens deletadas for do starboard
        # então podemos removê-la do banco de dados.
        sql = 'DELETE FROM starboard WHERE bot_message_id = ANY($1::bigint[]);'
        await self.bot.pool.execute(sql, list(payload.message_ids))

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        # Se todas as reações de uma mensagem forem deletadas
        # então podemos remover entradas desta mensagem do banco
        # de dados.
        sql = 'DELETE FROM starboard WHERE message_id = $1 RETURNING bot_message_id;'
        record = await self.bot.pool.fetchrow(sql, payload.message_id)

        if not record:
            return

        bot_message_id = record[0]
        message = await self.get_message(self.starboard, bot_message_id)

        if message:
            await message.delete()

    async def reaction_action(self, fmt: str, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != '⭐':
            return

        channel = self.bot.cosmic.get_channel(payload.channel_id)

        if not isinstance(channel, discord.TextChannel):
            return

        method = getattr(self, f'{fmt}_message')
        user = payload.member or (await self.get_or_fetch_member(payload.user_id))

        if not user or user.bot:
            return

        try:
            await method(channel, payload.message_id, payload.user_id)
        except StarError:
            pass

    async def get_or_fetch_member(self, member_id: int) -> Optional[discord.Member]:
        '''Tenta pegar um membro do cache, caso não consiga, faz
        uma requisição HTTP.

        Parameters
        ----------
        member_id: :class:`int`
            O ID do membro.

        Returns
        -------
        Optional[:class:`discord.Member`]
            O membro desejado ou `None` caso não tenha sido encontrado.
        '''
        member = self.bot.cosmic.get_member(member_id)

        if member:
            return member

        try:
            return await self.bot.cosmic.fetch_member(member_id)
        except discord.HTTPException:
            return None

    async def star_message(self, channel: discord.TextChannel, message_id: int, starrer_id: int):
        '''Adiciona uma estrela a uma mensagem.

        Parameters
        ----------
        channel: :class:`discord.TextChannel`
            O canal onde a mensagem pertence.
        message_id: :class:`int`
            O ID da mensagem.
        starrer_id: :class:`int`
            O ID de quem adicionou a estrela.
        '''
        if channel == self.star_message:
            # Um caso especial aqui, quando adicioanr uma estrela
            # em uma mensagem do starboard nós queremos adicionar
            # uma estrela na mensagem original.
            sql = 'SELECT channel_id, message_id FROM starboard WHERE bot_message_id = $1;'
            record = await self.bot.pool.fetchrow(sql, message_id)

            if not record:
                raise StarError('Could not find message in the starboard.')

            channel = self.bot.cosmic.get_channel(record['channel_id'])

            if not channel:
                raise StarError('Could not find original message')

            return await self.star_message(channel, record['message_id'], starrer_id)

        message = await self.get_message(channel, message_id)

        if not message_id:
            raise StarError('This message could not be found')

        if message.author.id == starrer_id:
            raise StarError('You cannot star your own message')

        has_no_content = len(message.content) == 0 and len(message.attachments) == 0
        is_not_default = message.type is not discord.MessageType.default

        if has_no_content or is_not_default:
            raise StarError('This message cannot be starred')

        oldest_allowed = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        if message.created_at < oldest_allowed:
            raise StarError('This message is too old')

        sql = '''
            WITH to_insert AS (
                INSERT INTO starboard AS entries (message_id, channel_id, author_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (message_id) DO NOTHING
                RETURNING entries.id
            )
            INSERT INTO starrers (author_id, entry_id)
            SELECT $4, entry.id
            FROM (
                SELECT id FROM to_insert
                UNION ALL
                SELECT id FROM starboard WHERE message_id = $1
                LIMIT 1
            ) AS entry
            RETURNING entry_id;
        '''

        try:
            record = await self.bot.pool.fetchrow(sql, message_id, channel.id, message.author.id, starrer_id)
        except asyncpg.UniqueViolationError:
            raise StarError('You already starred this message')

        entry_id = record[0]

        sql = 'SELECT COUNT(*) FROM starrers WHERE entry_id = $1;'
        record = await self.bot.pool.fetchrow(sql, entry_id)

        count = record[0]

        if count < THRESHOLD:
            return

        # A partir desse ponto nós criamos uma mensagem
        # no starboard ou editamos caso ela já exista.
        content, embed = self.get_content(message, count)

        # Pegar o ID da mensagem a ser editada.
        sql = 'SELECT bot_message_id FROM starboard WHERE message_id = $1;'
        record = await self.bot.pool.fetchrow(sql, message_id)

        bot_message_id = record[0]

        if not bot_message_id:
            # Caso ela não exista então criamos ela.
            new_message = await self.starboard.send(content, embed=embed)

            sql = 'UPDATE starboard SET bot_message_id = $2 WHERE message_id = $1;'
            await self.bot.pool.execute(sql, message_id, new_message.id)
        else:
            new_message = await self.get_message(self.starboard, bot_message_id)

            if not new_message:
                # Mensagem provavelmente deleta, então deletamos
                # do banco de dados.
                sql = 'DELETE FROM starboard WHERE message_id = $1;'
                await self.bot.pool.execute(sql, message_id)
            else:
                await new_message.edit(content=content, embed=embed)

    async def unstar_message(self, channel: discord.TextChannel, message_id: int, starrer_id: int):
        '''Remove uma estrela de uma mensagem.

        Parameters
        ----------
        channel: :class:`discord.TextChannel`
            O canal onde a mensagem pertence.
        message_id: :class:`int`
            O ID da mensagem.
        starrer_id: :class:`int`
            O ID de quem removeu a estrela.
        '''   
        if channel == self.star_message:
            # Leia a linha 175-177.
            sql = 'SELECT channel_id, message_id FROM starboard WHERE bot_message_id = $1;'
            record = await self.bot.pool.fetchrow(sql, message_id)

            if not record:
                raise StarError('Could not find message in the starboard.')

            channel = self.bot.cosmic.get_channel(record['channel_id'])

            if not channel:
                raise StarError('Could not find original message')

            return await self.unstar_message(channel, record['message_id'], starrer_id)

        sql = '''
            DELETE FROM starrers 
            USING starboard entry
            WHERE entry.message_id = $1 
            AND entry.id = starrers.entry_id 
            AND starrers.author_id = $2
            RETURNING starrers.entry_id, entry.bot_message_id
        '''
        record = await self.bot.pool.fetchrow(sql, message_id, starrer_id)

        if not record:
            raise StarError('You have not starred this message')

        entry_id = record[0]
        bot_message_id = record[1]

        sql = 'SELECT COUNT(*) FROM starrers WHERE entry_id = $1;'
        record = await self.bot.pool.fetchrow(sql, entry_id)
        
        count = record[0]

        if count == 0:
            # Removemos caso não haja mais estrelas.
            sql = 'DELETE FROM starboard WHERE id = $1;'
            await self.bot.pool.execute(sql, entry_id)

        if not bot_message_id:
            return

        bot_message = await self.get_message(self.starboard, bot_message_id)

        if not bot_message:
            return

        if count < THRESHOLD:
            if count:
                # Atualizar a mensagem do starboard já que estamos deletando ela.
                sql = 'UPDATE starboard SET bot_message_id = NULL WHERE id = $1;'
                await self.bot.pool.execute(sql, entry_id)

            await bot_message.delete()
        else:
            message = await self.get_message(channel, message_id)

            if not message:
                raise StarError('This message could not be found')

            content, embed = self.get_content(message, count)
            await bot_message.edit(content=content, embed=embed)        

    async def get_message(self, channel: discord.TextChannel, message_id: int) -> Optional[discord.Message]:
        '''Tenta pegar uma mensagem do cache, caso não consiga
        faz uma requisição HTTP.

        Parameters
        ----------
        channel: :class:`discord.TextChannel`
            O canal onde a mensagem pertence.
        message_id: :class:`int`
            O ID da mensagem desejada.

        Returns
        -------
        Optional[:class:`discord.Message`]
            A mensagem desejada, ou `None` caso não tenha sido encontrada.
        '''
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

    def get_star_emoji(self, count: int) -> str:
        '''Retorna um emoji diferente dependendo da quantidade de estrelas.'''        
        if 5 > count >= 0:
            return '⭐'
        elif 10 > count >= 5:
            return '🌟'
        elif 25 > count >= 10:
            return '💫'
        else:
            return '✨'

    def get_content(self, message: discord.Message, stars: int) -> tuple[str, discord.Embed]:
        '''Retorna o conteúdo e a embed para serem usados no starboard.

        Parameters
        ----------
        message: :class:`discord.Message`
            A mensagem para ser usada de base.
        stars: :class:`int`
            A quantidade de estrelas

        Returns
        -------
        tuple[:class:`str`, :class:`discord.Embed`]
            O conteúdo e a embed para serem usados no starboard.
        '''
        emoji = self.get_star_emoji(stars)

        if stars > 1:
            content = f'{emoji} **{stars}** │ {message.channel.mention}'
        else:
            content = f'{emoji} │ {message.channel.mention}'

        embed = discord.Embed(description=message.content)

        if message.embeds:
            data = message.embeds[0]

            if data.type == 'image' and not self.is_url_spoiler(message.content, data.url):
                embed.set_image(url=data.url)

        if message.attachments:
            file = message.attachments[0]
            spoiler = file.is_spoiler()

            valid_images = ('png', 'jpeg', 'jpg', 'gif', 'webp')
            if not spoiler and file.url.lower().endswith(valid_images):
                embed.set_image(url=file.url)
            elif spoiler:
                embed.add_field(name='Anexo', value=f'||[{file.filename}]({file.url})||', inline=False)
            else:
                embed.add_field(name='Anexo', value=f'[{file.filename}]({file.url})', inline=False)

        embed.add_field(name='Mensagem original', value=f'[Clique aqui]({message.jump_url})')
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
        embed.colour = self.star_gradient_colour(stars)

        return content, embed

    def is_url_spoiler(self, text: str, url: str) -> bool:
        '''Verifica se um link é marcado como spoiler em um texto.

        Parameters
        ----------
        text: :class:`str`
            O texto a ser testado.
        url: :class:`str`
            A URL a ser procurada.

        Returns
        -------
        :class:`bool`
            Booleano que indica se a URL é um spoiler.
        '''
        spoilers = self.spoilers.findall(text)

        for spoiler in spoilers:
            if url in spoiler:
                return True

        return False

    def star_gradient_colour(self, count: int) -> int:
        '''Retorna um tom de amarelo baseado na quantidade de estrelas.

        Parameters
        ----------
        count: :class:`int`
            A quantidade de estrelas.

        Returns
        -------
        :class:`int`
            Um inteiro que representa a cor na :class:`discord.Embed`.
        '''

        # Definimos 13 como 100% do nosso gradiente de amarelo.
        # Começamos com `0xfffdf7` como a cor inicial e
        # vai gradualmente subindo para `0xffc20c`.
        # Para criar o degradê, usamos uma fórmula de interpolação
        # linear. A referência é:
        # `X = X_1 * p + X_2 * (1 - p)`
        p = count / 13

        if p > 1.0:
            p = 1.0

        red = 255
        green = int((194 * p) + (253 * (1 - p)))
        blue = int((12 * p) + (247 * (1 - p)))
        
        return (red << 16) + (green << 8) + blue


def setup(bot: Eris):
    bot.add_cog(Starboard(bot))
