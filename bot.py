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
    app.router.add_get("/health", health)   # endpoint /health dla Render healthcheck
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

# ---------- lista dźwięków w pamięci (bez plików) ----------
# Opcjonalnie: startowe wpisy w ENV SOUNDS_JSON, np. {"chrupiaca":"https://.../qicCm.mp3"}
SOUNDS: dict[str, str] = {}
try:
    env_json = os.getenv("SOUNDS_JSON")
    if env_json:
        SOUNDS = json.loads(env_json)
        if not isinstance(SOUNDS, dict):
            SOUNDS = {}
except Exception:
    SOUNDS = {}

# ---------- status ----------
@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="!playsound / !kulawy list")
    )

# ---------- komenda zabawowa ----------
@bot.command(name="kondom")
async def kondom(ctx: commands.Context, member: discord.Member = None):
    # jeśli ktoś został oznaczony, to on jest targetem; jeśli nie, to autor
    target = member if member else ctx.author

    # jeżeli target albo autor to "derbengaming"
    if target.name.lower() == "derbengaming" or ctx.author.name.lower() == "derbengaming":
        value = random.choice([99, 100])
    else:
        value = random.randint(1, 100)

    # odpowiedź
    if member:
        await ctx.send(f"{member.mention} jest kondomem w {value}% PykPykPyk!")
    else:
        await ctx.send(f"Jesteś kondomem w {value}%")

# ---------- soundboard: create/list (bez trwałego zapisu) ----------
@bot.command(name="kulawy")
async def kulawy(ctx: commands.Context, subcommand: str = None, name: str = None, url: str = None):
    if subcommand == "create":
        if not name or not url:
            return await ctx.send("Użycie: `!kulawy create NAZWA LINK`")
        SOUNDS[name] = url
        # Uwaga: brak zapisu do pliku; po restarcie zniknie, chyba że dodasz do ENV SOUNDS_JSON
        return await ctx.send(f"✅ Dodałem dźwięk **{name}** → {url}")
    elif subcommand == "list":
        if not SOUNDS:
            return await ctx.send("❌ Brak zapisanych dźwięków.")
        lines = "\n".join(f"• {k} → {v}" for k, v in SOUNDS.items())
        return await ctx.send(f"📀 Zapisane dźwięki:\n{lines}")
    else:
        return await ctx.send("Użycie: `!kulawy create NAZWA LINK` lub `!kulawy list`")

# ---------- test: ręczne join/leave ----------
@bot.command(name="join")
async def join(ctx: commands.Context):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("Wejdź najpierw na kanał głosowy.")
    ch = ctx.author.voice.channel
    try:
        if ctx.voice_client and ctx.voice_client.channel != ch:
            await ctx.voice_client.move_to(ch)
        elif not ctx.voice_client:
            await ch.connect()
        await ctx.send(f"✅ Połączono z **{ch.name}**")
        print(f"[voice] connected to: {ch} (guild={ctx.guild.id})")
    except Exception as e:
        await ctx.send(f"❌ Nie mogę dołączyć: `{type(e).__name__}: {e}`")
        print("[voice][join] error:", repr(e))

@bot.command(name="leave")
async def leave(ctx: commands.Context):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Rozłączono.")
    else:
        await ctx.send("Nie jestem na żadnym kanale.")

# ---------- playsound: join + play + auto-leave ----------
@bot.command(name="playsound")
async def playsound(ctx: commands.Context, name_or_url: str = None):
    if not name_or_url:
        return await ctx.send("Podaj nazwę dźwięku lub URL, np. `!playsound chrupiaca`")

    # 1) znajdź źródło
    if name_or_url in SOUNDS:
        source_url = SOUNDS[name_or_url]
        pretty = name_or_url
    else:
        source_url = name_or_url  # potraktuj argument jako URL
        pretty = source_url

    # 2) użytkownik musi być na voice
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("Wejdź najpierw na kanał głosowy.")

    ch = ctx.author.voice.channel

    # 3) połączenie
    try:
        vc: discord.VoiceClient | None = ctx.voice_client
        if vc and vc.channel != ch:
            await vc.move_to(ch)
        elif not vc:
            print(f"[voice] connecting to: {ch} (guild={ctx.guild.id})")
            vc = await ch.connect()
    except Exception as e:
        await ctx.send(f"❌ Nie mogę dołączyć do **{ch.name}**: `{type(e).__name__}: {e}`")
        print("[voice][connect] error:", repr(e))
        return

    # 4) odtwórz audio (FFmpeg wymagany w systemie)
    try:
        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn"
        }
        if vc.is_playing():
            vc.stop()
        audio = discord.FFmpegPCMAudio(source_url, **ffmpeg_options)
        # (opcjonalnie) głośność:
        # audio = discord.PCMVolumeTransformer(audio, volume=0.8)

        vc.play(audio)
        await ctx.send(f"▶️ Gram: **{pretty}**")
        print(f"[voice] playing: {source_url}")

        while vc.is_playing():
            await asyncio.sleep(0.5)
        await vc.disconnect()
        print("[voice] finished and disconnected")
    except FileNotFoundError as e:
        # zwykle brak ffmpeg w systemie
        await ctx.send("❌ Nie mogę odtworzyć – wygląda na brak FFmpeg na serwerze.")
        print("[voice][ffmpeg] not found:", repr(e))
    except Exception as e:
        await ctx.send(f"❌ Błąd odtwarzania: `{type(e).__name__}: {e}`")
        print("[voice][play] error:", repr(e))

# ---------- uruchomienie równoległe ----------
async def main():
    # serwer HTTP + bot równolegle
    http_task = asyncio.create_task(start_http_server())

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Brak DISCORD_TOKEN w zmiennych środowiskowych")

    bot_task = asyncio.create_task(bot.start(token))

    done, _ = await asyncio.wait({http_task, bot_task}, return_when=asyncio.FIRST_EXCEPTION)
    for t in done:
        exc = t.exception()
        if exc:
            raise exc

if __name__ == "__main__":
    asyncio.run(main())
