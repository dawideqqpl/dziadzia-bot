import discord
from discord.ext import commands
import json
import os

INTENTS = discord.Intents.default()
INTENTS.message_content = True
bot = commands.Bot(command_prefix="!", intents=INTENTS)

SOUNDS_FILE = "sounds.json"

# wczytaj dźwięki z pliku
if os.path.exists(SOUNDS_FILE):
    with open(SOUNDS_FILE, "r", encoding="utf-8") as f:
        sounds = json.load(f)
else:
    sounds = {}

def save_sounds():
    with open(SOUNDS_FILE, "w", encoding="utf-8") as f:
        json.dump(sounds, f, indent=2, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")

# -------------------
# !kulawy create NAZWA LINK
# -------------------
@bot.command(name="kulawy")
async def kulawy(ctx, subcommand: str, name: str = None, url: str = None):
    if subcommand == "create":
        if not name or not url:
            return await ctx.send("Użycie: `!kulawy create NAZWA LINK`")
        sounds[name] = url
        save_sounds()
        await ctx.send(f"✅ Dodałem dźwięk **{name}** → {url}")

    elif subcommand == "list":
        if not sounds:
            return await ctx.send("❌ Brak zapisanych dźwięków.")
        msg = "\n".join([f"• {k} → {v}" for k, v in sounds.items()])
        await ctx.send(f"📀 Zapisane dźwięki:\n{msg}")

# -------------------
# !playsound NAZWA
# -------------------
@bot.command(name="playsound")
async def playsound(ctx, name: str = None):
    if not name:
        return await ctx.send("Podaj nazwę dźwięku, np. `!playsound chrupiaca`")

    if name not in sounds:
        return await ctx.send(f"❌ Nie znam dźwięku **{name}**")

    url = sounds[name]

    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("Wejdź najpierw na kanał głosowy.")

    voice_channel = ctx.author.voice.channel
    vc: discord.VoiceClient | None = ctx.voice_client
    if vc and vc.channel != voice_channel:
        await vc.move_to(voice_channel)
    elif not vc:
        vc = await voice_channel.connect()

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    audio = discord.FFmpegPCMAudio(url, **ffmpeg_options)
    vc.play(audio)

    await ctx.send(f"▶️ Gram: **{name}**")

    while vc.is_playing():
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.utcnow().__class__.resolution)
    await vc.disconnect()
