import os
import json
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

SOUNDS_FILE = "sounds.json"
if os.path.exists(SOUNDS_FILE):
    with open(SOUNDS_FILE, "r", encoding="utf-8") as f:
        SOUNDS = json.load(f)
else:
    SOUNDS = {}

def save_sounds():
    with open(SOUNDS_FILE, "w", encoding="utf-8") as f:
        json.dump(SOUNDS, f, indent=2, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="!kondom / !playsound")
    )

# ------------------- Komenda zabawowa -------------------
@bot.command(name="kondom")
async def kondom(ctx: commands.Context, member: discord.Member = None):
    value = random.randint(1, 100)
    if member:
        await ctx.send(f"{member.mention} jest kondomem w {value}% PykPykPyk!")
    else:
        await ctx.send(f"Jesteś kondomem w {value}%")

# ------------------- Soundboard: create/list -------------------
@bot.command(name="kulawy")
async def kulawy(ctx: commands.Context, subcommand: str = None, name: str = None, url: str = None):
    if subcommand == "create":
        if not name or not url:
            return await ctx.send("Użycie: `!kulawy create NAZWA LINK`")
        SOUNDS[name] = url
        save_sounds()
        return await ctx.send(f"✅ Dodałem dźwięk **{name}** → {url}")
    elif subcommand == "list":
        if not SOUNDS:
            return await ctx.send("❌ Brak zapisanych dźwięków.")
        lines = "\n".join(f"• {k} → {v}" for k, v in SOUNDS.items())
        return await ctx.send(f"📀 Zapisane dźwięki:\n{lines}")
    else:
        return await ctx.send("Użycie: `!kulawy create NAZWA LINK` lub `!kulawy list`")

# ------------------- Odtwarzanie: join + play + leave -------------------
@bot.command(name="playsound")
async def playsound(ctx: commands.Context, name_or_url: str = None):
    if not name_or_url:
        return await ctx.send("Podaj nazwę dźwięku lub URL, np. `!playsound chrupiaca`")

    # 1) znajdź źródło
    if name_or_url in SOUNDS:
        source_url = SOUNDS[name_or_url]
        pretty = name_or_url
    else:
        source_url = name_or_url   # potraktuj argument jak bezpośredni URL
        pretty = source_url

    # 2) upewnij się, że autor jest na kanale głosowym
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("Wejdź najpierw na kanał głosowy.")

    voice_channel = ctx.author.voice.channel

    # 3) połącz się z kanałem (lub przenieś)
    vc: discord.VoiceClient | None = ctx.voice_client
    if vc and vc.channel != voice_channel:
        await vc.move_to(voice_channel)
    elif not vc:
        vc = await voice_channel.connect()

    await ctx.send(f"▶️ Gram: **{pretty}**")

    # 4) odtwórz przez FFmpeg
    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }
    audio = discord.FFmpegPCMAudio(source_url, **ffmpeg_options)
    # (opcjonalnie głośność)
    # audio = discord.PCMVolumeTransformer(audio, volume=0.75)

    # zatrzymaj ewentualne poprzednie audio i puść nowe
    if vc.is_playing():
        vc.stop()
    vc.play(audio)

    # 5) czekaj aż skończy, potem wyjdź
    while vc.is_playing():
        await asyncio.sleep(0.5)
    await vc.disconnect()

# ------------------- uruchomienie równoległe -------------------
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
