import discord
from discord.ext import commands


# TODO: Adicionar uma documentação decente.

class Bellatrix(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='b/', intents=discord.Intents.all())