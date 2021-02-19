import discord
from discord.ext import commands


NITRO_BOOSTER_ROLE_ID = 804077079788257300


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.nitro_booster_role = bot.cosmic.get_role(NITRO_BOOSTER_ROLE_ID)

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
                description=f'Uma chuva de aplausos! {after.mention} impulsionou o servidor! ❤️'
                color=self.nitro_booster_role.color
            )

            await general_channel.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Events(bot))
