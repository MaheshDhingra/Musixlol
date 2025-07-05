import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from discord.utils import get
from discord import FFmpegPCMAudio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from yt_dlp import YoutubeDL

load_dotenv()

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = commands.Bot(command_prefix='!', intents=intents)

# Spotify API Setup
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')

if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    print("Error: Spotify API credentials not found in .env file.")
    print("Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET.")
    exit()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID,
                                                           client_secret=SPOTIPY_CLIENT_SECRET))

players = {}

@client.event
async def on_ready():
    print('Musixlol Bot online and connected to Spotify!')

@client.command()
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()
    await ctx.send(f"Joined {channel.name}")

@client.command()
async def play(ctx, *, query):
    voice = get(client.voice_clients, guild=ctx.guild)
    if not voice:
        await ctx.send("I am not in a voice channel. Please use `!join` first.")
        return

    if voice.is_playing():
        await ctx.send("I'm already playing something. Please wait or use `!stop` first.")
        return

    try:
        # Search Spotify for the track
        spotify_results = sp.search(q=query, type='track', limit=1)
        if not spotify_results['tracks']['items']:
            await ctx.send(f"Could not find any tracks for '{query}' on Spotify.")
            return

        track = spotify_results['tracks']['items'][0]
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        
        # Use yt-dlp to find and stream the audio from YouTube
        YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True', 'default_search': 'ytsearch'}
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

        search_query = f"{track_name} {artist_name}"
        await ctx.send(f"Searching YouTube for: **{track_name}** by **{artist_name}**...")

        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if 'entries' in info:
                # Take the first entry from the search results
                info = info['entries'][0]
            URL = info['url']
        
        voice.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
        voice.is_playing()
        await ctx.send(f"Now playing: **{track_name}** by **{artist_name}**")

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        print(f"Error in play command: {e}")

@client.command()
async def resume(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_paused():
        voice.resume()
        await ctx.send('Bot is resuming')
    else:
        await ctx.send('Bot is not paused.')

@client.command()
async def pause(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_playing():
        voice.pause()
        await ctx.send('Bot has been paused')
    else:
        await ctx.send('Bot is not playing or already paused.')

@client.command()
async def stop(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and (voice.is_playing() or voice.is_paused()):
        voice.stop()
        await ctx.send('Stopping...')
    else:
        await ctx.send('Bot is not playing anything.')

@client.command()
async def leave(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I am not in a voice channel.")

@client.command()
async def clear(ctx, amount=5):
    await ctx.channel.purge(limit=amount + 1) # +1 to clear the command message itself
    await ctx.send(f"Cleared {amount} messages.", delete_after=5) # Delete confirmation after 5 seconds

client.run(os.getenv('TOKEN'))
