import discord
from discord.ext import commands, menus


class _MenuBase(menus.Menu):
    async def update(self, payload: discord.RawReactionActionEvent):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            else:
                return

        await super().update(payload)

class PunishmentMenu(_MenuBase):
    def __init__(self):
        super().__init__(delete_message_after=True)

        self.reason = None
        self._reasons = [
            'Violação das Diretrizes do Discord',
            'Má convivência',
            'Flood/Spam',
            'Divulgação',
            'Desrespeito aos tópicos',
            'Poluição sonora'
        ]

        for i in range(1, len(self._reasons) + 1):
            emoji = f'{i}\N{variation selector-16}\N{combining enclosing keycap}'
            button = menus.Button(emoji, self.on_reason)

            self.add_button(button)

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
        reasons = []
        for i, reason in enumerate(self._reasons, start=1):
            emoji = f'{i}\N{variation selector-16}\N{combining enclosing keycap}'
            reasons.append(f'{emoji} - {reason}')

        return await ctx.reply('\n'.join(reasons))

    async def on_reason(self, payload: discord.RawReactionActionEvent):
        index = int(str(payload.emoji)[0]) - 1
        self.reason = self._reasons[index]
        self.stop()

    async def prompt(self, ctx: commands.Context):
        await self.start(ctx, wait=True)
        return self.reason