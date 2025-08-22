import os
import random
import discord
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()
intents = discord.Intents.default()
intents.message_content = True  # wymagane dla komend z prefiksem (!)

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")

@bot.command(name="kondom")
async def kondom(ctx: commands.Context):
    value = random.randint(1, 100)
    await ctx.send(f"Jesteś kondomem w {value}%")

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))

