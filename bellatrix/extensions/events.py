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

import discord
from discord.ext import commands


NITRO_BOOSTER_ROLE_ID = 804077079788257300


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.nitro_booster_role = bot.cosmic.get_role(NITRO_BOOSTER_ROLE_ID)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        embed = discord.Embed(
            title='Um membro entrou no servidor!',
            description=f'{member.mention} entrou no servidor! ❤️\n\nNão se esqueça de ler as <#795029002225451048>!',
            color=guild.me.color
        )

        await self.bot.general_channel.send(member.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return

        has_boosted_before = self.nitro_booster_role in before.roles
        has_boosted_after = self.nitro_booster_role in after.roles

        if not has_boosted_before and has_boosted_after:
            general_channel = self.bot.general_channel
            guild = after.guild

            embed = discord.Embed(
                title=f'{after.name} impulsionou o servidor!',
                description=f'Uma chuva de aplausos! {after.mention} impulsionou o servidor! ❤️',
                color=self.nitro_booster_role.color
            )

            await general_channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Events(bot))
