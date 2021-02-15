from discord.ext import commands


STAFF_ROLE_ID = 795026574453899304
PREMIUM_ROLE_ID = 810879208359723038
NITRO_BOOSTER_ROLE_ID = 804077079788257300

ONLY_PREMIUM = (
    STAFF_ROLE_ID,
    PREMIUM_ROLE_ID,
    NITRO_BOOSTER_ROLE_ID
)

def is_premium():
    def predicate(ctx: commands.Context):
        return any(role.id in ONLY_PREMIUM for role in ctx.author.roles)

    return commands.check(predicate)

def is_staffer():
    def predicate(ctx: commands.Context):
        return STAFF_ROLE_ID in [role.id for role in ctx.author.roles]

    return commands.check(predicate)