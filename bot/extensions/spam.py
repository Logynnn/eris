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

import logging
from datetime import timezone

import discord
from discord.ext import commands
from discord.ext.commands import CooldownMapping, BucketType


log = logging.getLogger(__name__)


class CooldownByContent(CooldownMapping):
    def _bucket_key(self, message: discord.Message):
        return (message.channel.id, message.content)


class SpamChecker:
    def __init__(self):
        self.by_content = CooldownByContent.from_cooldown(15, 17.0, BucketType.member)
        self.by_user = CooldownMapping.from_cooldown(10, 12.0, BucketType.user)

    def is_spamming(self, message: discord.Message) -> bool:
        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()

        user_bucket = self.by_user.get_bucket(message)
        if user_bucket.update_rate_limit(current):
            return True

        content_bucket = self.by_content.get_bucket(message)
        if content_bucket.update_rate_limit(current):
            return True

        return False


class Spam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_checker = SpamChecker()

    async def check_raid(self, message: discord.Message) -> bool:
        checker = self.spam_checker
        author = message.author

        if not checker.is_spamming(message):
            return False

        try:
            await author.ban(reason='Autoban from spam')
        except Exception:
            fmt = 'Failed to autoban {0} ({0.id}) by spam'
        else:
            fmt = 'Banned {0} ({0.id}) by spam'
        finally:
            log.info(fmt.format(author))
            return True

    @commands.Cog.listener()
    async def on_regular_message(self, message: discord.Message):
        author = message.author

        if len(author.roles):
            return

        if await self.check_raid(message):
            return

        mentions_count = len(message.raw_mentions) + len(message.raw_role_mentions)

        if mentions_count <= 3:
            return

        try:
            await author.ban(reason=f'Spamming de menções ({mentions_count} menções)')
        except Exception:
            fmt = 'Failed to autoban {0} ({0.id}) for spamming {1} mentions'
        else:
            fmt = 'Member {0} ({0.id}) has been autobanned for spamming mentions ({1} mentions)'
        finally:
            log.info(fmt.format(author, mentions_count))
        

def setup(bot: commands.Bot):
    bot.add_cog(Spam(bot))