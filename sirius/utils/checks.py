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
