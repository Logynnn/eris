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

import string

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cosmic = bot.cosmic

        self.general_channel = bot.general_channel
        self.nitro_booster_role = bot.nitro_booster_role

        bot.loop.create_task(self.sanitize_all_nicknames())

    async def sanitize_all_nicknames(self):
        for member in self.cosmic.members:
            if member.bot:
                continue

            await self.sanitize_nickname(member)

    async def sanitize_nickname(self, member: discord.Member):
        if member.guild_permissions.administrator:
            return

        display_name = member.display_name
        sanitized = ''.join([str(char) for char in display_name if char in string.printable])

        if display_name == sanitized:
            return

        await member.edit(reason=f'Apelido sanitizado', nick=sanitized)

    async def send_welcome(self, member: discord.Member):
        if member.bot:
            return

        embed = discord.Embed(
            title='Um membro entrou no servidor!',
            description=f'{member.mention} entrou no servidor! ❤️\n\nNão se esqueça de ler as <#795029002225451048>!',
            color=self.bot.color
        )

        await self.general_channel.send(member.mention, embed=embed)
    
    # TODO: Fazer uma mensagem de bem-vindo agradável.
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.sanitize_nickname(member)
        await self.send_welcome(member)

    # RELATED: https://github.com/discord/discord-api-docs/issues/1182
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name != after.display_name:
            return await self.sanitize_nickname(after)

        if before.roles == after.roles:
            return

        has_boosted_before = self.nitro_booster_role in before.roles
        has_boosted_after = self.nitro_booster_role in after.roles

        if not has_boosted_before and has_boosted_after:
            embed = discord.Embed(
                title=f'{after.name} impulsionou o servidor!',
                description=f'Uma chuva de aplausos! {after.mention} impulsionou o servidor! ❤️',
                color=self.nitro_booster_role.color
            )

            await self.general_channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Events(bot))
