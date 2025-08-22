import os
import random
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# --- prosty serwer HTTP dla Render ---
from aiohttp import web

async def health(_):
    return web.Response(text="ok")

async def start_http_server():
    app = web.Application()
    app.router.add_get("/health", health)   # <-- endpoint /health
    port = int(os.getenv("PORT", "10000"))  # Render ustawia PORT automatycznie
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    print(f"[web] listening on 0.0.0.0:{port} (health at /health)")

# --- Discord bot ---
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True  # pamiętaj też włączyć w Dev Portal

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="!kondom")
    )

@bot.command(name="kondom")
async def kondom(ctx: commands.Context, *, _rest: str = ""):
    # bierz pierwszy mention z wiadomości, jeśli jest
    member = ctx.message.mentions[0] if ctx.message.mentions else None

    value = random.randint(1, 100)
    if member:
        await ctx.send(f"{member.mention} jest kondomem w {value}% PykPykPyk!")
    else:
        await ctx.send(f"Jesteś kondomem w {value}%")


async def main():
    # serwer HTTP + bot równolegle
    http_task = asyncio.create_task(start_http_server())

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Brak DISCORD_TOKEN w zmiennych środowiskowych")

    bot_task = asyncio.create_task(bot.start(token))

    done, pending = await asyncio.wait(
        {http_task, bot_task},
        return_when=asyncio.FIRST_EXCEPTION
    )
    for t in done:
        exc = t.exception()
        if exc:
            raise exc

if __name__ == "__main__":
    asyncio.run(main())
