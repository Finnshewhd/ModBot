import discord
from discord.ext import commands
import json
import time

# Lade die Konfigurationsdatei
with open('config.json') as f:
    config = json.load(f)

# Bot-Einstellungen
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

# In-Memory-Datenbank für Warnungen und Anti-Spam
warns = {}
spam_records = {}

# Event: Bot ist bereit
@bot.event
async def on_ready():
    print(f'Bot ist eingeloggt als {bot.user.name}')

# Anti-Spam-Feature
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    current_time = time.time()
    author_id = message.author.id

    if author_id not in spam_records:
        spam_records[author_id] = []

    # Entferne alte Nachrichten außerhalb des Spam-Zeitfensters
    spam_records[author_id] = [msg_time for msg_time in spam_records[author_id] if current_time - msg_time < config['spam_timeframe']]

    # Füge die aktuelle Nachricht hinzu
    spam_records[author_id].append(current_time)

    # Überprüfe, ob die Nachrichtenzahl den Spam-Schwellenwert überschreitet
    if len(spam_records[author_id]) > config['spam_threshold']:
        await message.channel.send(f'{message.author.mention}, du wurdest wegen Spamming gewarnt.')
        await warn_user(message.author, message.guild)
        return

    await bot.process_commands(message)

# Warnsystem
async def warn_user(user, guild):
    if user.id not in warns:
        warns[user.id] = 0
    
    warns[user.id] += 1
    if warns[user.id] >= config['warn_limit']:
        await guild.kick(user, reason="Zu viele Warnungen")
        await user.send(f'Du wurdest von {guild.name} gekickt wegen zu vieler Warnungen.')
        del warns[user.id]
    else:
        await user.send(f'Du wurdest gewarnt. Anzahl der Warnungen: {warns[user.id]}')

# Moderationsbefehle
@commands.has_role(config['moderator_role'])
@bot.command(name='kick')
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'{member.name} wurde gekickt. Grund: {reason}')

@commands.has_role(config['admin_role'])
@bot.command(name='ban')
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'{member.name} wurde gebannt. Grund: {reason}')

@commands.has_role(config['admin_role'])
@bot.command(name='unban')
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name == member_name:
            await ctx.guild.unban(user)
            await ctx.send(f'{user.name} wurde entbannt.')
            return
    await ctx.send(f'{member_name} wurde nicht gefunden.')

# Warnbefehle
@commands.has_role(config['moderator_role'])
@bot.command(name='warn')
async def warn(ctx, member: discord.Member, *, reason=None):
    await warn_user(member, ctx.guild)
    await ctx.send(f'{member.name} wurde gewarnt. Grund: {reason}')

@commands.has_role(config['admin_role'])
@bot.command(name='clearwarns')
async def clear_warns(ctx, member: discord.Member):
    if member.id in warns:
        del warns[member.id]
        await ctx.send(f'Warnungen für {member.name} wurden gelöscht.')
    else:
        await ctx.send(f'{member.name} hat keine Warnungen.')

# Logging
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name='log')
    if channel:
        await channel.send(f'{member.name} ist dem Server beigetreten.')

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.channels, name='log')
    if channel:
        await channel.send(f'{member.name} hat den Server verlassen.')

# Fehlerbehandlung für fehlende Berechtigungen
@kick.error
@ban.error
@unban.error
@warn.error
@clear_warns.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("Du hast keine Berechtigung, diesen Befehl zu verwenden.")

# Starte den Bot
bot.run(config['token'])
