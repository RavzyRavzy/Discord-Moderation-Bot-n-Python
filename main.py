import os
import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import colorlog
from datetime import datetime, timezone
from pathlib import Path
import traceback
import json

import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
from dotenv import load_dotenv

def setup_logging() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger("ModerationBot")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    file_handler = RotatingFileHandler(
        filename=log_dir / 'moderation_bot.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

class DatabaseManager:
    def __init__(self, db_path: str = "data/moderation.db"):
        self.db_path = db_path
        self.db_dir = Path("data")
        self.db_dir.mkdir(exist_ok=True)
        logger.info(f"Veritabanı yöneticisi başlatılıyor: {db_path}")
    
    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS forcebans (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    banned_by INTEGER NOT NULL,
                    ban_reason TEXT,
                    ban_date TEXT NOT NULL,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS mutes (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    muted_by INTEGER NOT NULL,
                    mute_reason TEXT,
                    mute_date TEXT NOT NULL,
                    unmute_date TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS log_channels (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL,
                    log_events TEXT NOT NULL DEFAULT '{"message_delete":true,"message_edit":true,"member_join":true,"member_remove":true,"ban":true,"unban":true,"kick":true,"mute":true,"unmute":true,"role_change":true,"voice_state":true}'
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS mute_roles (
                    guild_id INTEGER PRIMARY KEY,
                    role_id INTEGER NOT NULL
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS mod_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    timestamp TEXT NOT NULL,
                    message_link TEXT
                )
            ''')
            await db.commit()
            logger.info("Veritabanı tabloları başarıyla oluşturuldu")
    
    async def add_forceban(self, user_id: int, guild_id: int, banned_by: int, reason: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO forcebans (user_id, guild_id, banned_by, ban_reason, ban_date) VALUES (?, ?, ?, ?, ?)",
                (user_id, guild_id, banned_by, reason, datetime.now(timezone.utc).isoformat())
            )
            await db.commit()
    
    async def remove_forceban(self, user_id: int, guild_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM forcebans WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def is_forcebanned(self, user_id: int, guild_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM forcebans WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            result = await cursor.fetchone()
            return result is not None

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)
tree = bot.tree
db_manager = DatabaseManager()

@bot.event
async def on_ready():
    await db_manager.initialize()
    logger.info(f"{bot.user} aktif! {len(bot.guilds)} sunucuda çalışıyor.")
    await tree.sync()
    if not status_loop.is_running():
        status_loop.start()

@tasks.loop(minutes=5)
async def status_loop():
    statuses = [
        f"/help | {len(bot.guilds)} sunucuda",
        f"{len(bot.users)} kullanıcıya hizmet veriyor",
        "Profesyonel Moderasyon Botu"
    ]
    activity = discord.Game(name=statuses[datetime.now().minute % len(statuses)])
    await bot.change_presence(status=discord.Status.online, activity=activity)

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")
        logger.info(f"Cog yüklendi: {filename}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Bu komutu kullanmak için yetkin yok!", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Gerekli argüman eksik!", delete_after=5)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Komut cooldown’da! Lütfen {round(error.retry_after,1)} saniye bekleyin.", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Böyle bir komut yok!", delete_after=5)
    else:
        await ctx.send(f"Hata oluştu: {str(error)}", delete_after=5)
        logger.error("Hata oluştu", exc_info=error)

@bot.event
async def on_guild_join(guild):
    log_channel = discord.utils.get(guild.text_channels, name="denetim-log")
    if not log_channel:
        overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=True)}
        log_channel = await guild.create_text_channel("denetim-log", overwrites=overwrites)

@bot.event
async def on_guild_remove(guild):
    logger.info(f"Sunucudan çıkarıldı: {guild.name}")

@tree.command(name="ping", description="Botun pingini gösterir")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)}ms")

@tree.command(name="info", description="Bot hakkında bilgi verir")
async def slash_info(interaction: discord.Interaction):
    embed = discord.Embed(title="Moderasyon Botu", color=0x00ff00)
    embed.add_field(name="Sunucular", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Kullanıcılar", value=f"{len(bot.users)}", inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency*1000)}ms", inline=True)
    embed.timestamp = datetime.now(timezone.utc)
    await interaction.response.send_message(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def restart(ctx):
    await ctx.send("Bot yeniden başlatılıyor...")
    await bot.close()
    os.execv(sys.executable, ['python'] + sys.argv)
    class Moderation(commands.Cog):
          def __init__(self, bot, db_manager: DatabaseManager):
        self.bot = bot
        self.db = db_manager

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member} sunucudan yasaklandı!")
            await self.log_mod_action(ctx.guild.id, ctx.author.id, member.id, "BAN", reason, ctx.message.jump_url)
        except Exception as e:
            await ctx.send("Ban işlemi başarısız!")
            logger.error("Ban hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def forceban(self, ctx, user_id: int, *, reason=None):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.ban(user, reason=reason)
            await self.db.add_forceban(user.id, ctx.guild.id, ctx.author.id, reason or "Yönetici tarafından")
            await ctx.send(f"{user} sunucudan force banlandı!")
            await self.log_mod_action(ctx.guild.id, ctx.author.id, user.id, "FORCEBAN", reason, None)
        except Exception as e:
            await ctx.send("Forceban başarısız!")
            logger.error("Forceban hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, user_id: int):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await self.db.remove_forceban(user.id, ctx.guild.id)
            await ctx.send(f"{user} yasağı kaldırıldı!")
            await self.log_mod_action(ctx.guild.id, ctx.author.id, user.id, "UNBAN", None, None)
        except Exception as e:
            await ctx.send("Unban başarısız!")
            logger.error("Unban hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member} sunucudan atıldı!")
            await self.log_mod_action(ctx.guild.id, ctx.author.id, member.id, "KICK", reason, ctx.message.jump_url)
        except Exception as e:
            await ctx.send("Kick işlemi başarısız!")
            logger.error("Kick hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            role = await ctx.guild.create_role(name="Muted")
            for ch in ctx.guild.channels:
                await ch.set_permissions(role, send_messages=False)
        try:
            await member.add_roles(role)
            now = datetime.now(timezone.utc).isoformat()
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO mutes (user_id, guild_id, muted_by, mute_reason, mute_date) VALUES (?, ?, ?, ?, ?)",
                    (member.id, ctx.guild.id, ctx.author.id, reason, now)
                )
                await db.commit()
            await ctx.send(f"{member} susturuldu!")
            await self.log_mod_action(ctx.guild.id, ctx.author.id, member.id, "MUTE", reason, ctx.message.jump_url)
        except Exception as e:
            await ctx.send("Mute başarısız!")
            logger.error("Mute hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unmute(self, ctx, member: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        try:
            await member.remove_roles(role)
            now = datetime.now(timezone.utc).isoformat()
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute(
                    "UPDATE mutes SET unmute_date=? WHERE user_id=? AND guild_id=?",
                    (now, member.id, ctx.guild.id)
                )
                await db.commit()
            await ctx.send(f"{member} artık konuşabilir!")
            await self.log_mod_action(ctx.guild.id, ctx.author.id, member.id, "UNMUTE", None, ctx.message.jump_url)
        except Exception as e:
            await ctx.send("Unmute başarısız!")
            logger.error("Unmute hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def nuke(self, ctx):
        try:
            await ctx.channel.purge()
            await ctx.send("Chat temizlendi!", delete_after=5)
            await self.log_mod_action(ctx.guild.id, ctx.author.id, ctx.author.id, "NUKE", None, None)
        except Exception as e:
            await ctx.send("Nuke başarısız!")
            logger.error("Nuke hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def giverol(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role)
            await ctx.send(f"{member} rol aldı: {role.name}")
            await self.log_mod_action(ctx.guild.id, ctx.author.id, member.id, "GIVEROL", f"Rol: {role.name}", None)
        except Exception as e:
            await ctx.send("Rol verme başarısız!")
            logger.error("Giverol hatası", exc_info=e)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def log(self, ctx):
        channel = discord.utils.get(ctx.guild.text_channels, name="denetim-log")
        if not channel:
            overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(send_messages=True)}
            channel = await ctx.guild.create_text_channel("denetim-log", overwrites=overwrites)
        await ctx.send(f"Denetim kanalı hazır: {channel.mention}")

    async def log_mod_action(self, guild_id, user_id, target_id, action, reason, message_link):
        timestamp = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.execute(
                "INSERT INTO mod_logs (guild_id, user_id, target_id, action, reason, timestamp, message_link) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (guild_id, user_id, target_id, action, reason, timestamp, message_link)
            )
            await db.commit()
        guild = self.bot.get_guild(guild_id)
        if guild:
            log_channel = discord.utils.get(guild.text_channels, name="denetim-log")
            if log_channel:
                embed = discord.Embed(title=f"Moderasyon | {action}", color=0xff0000, timestamp=datetime.now(timezone.utc))
                embed.add_field(name="Yetkili", value=f"<@{user_id}>", inline=True)
                embed.add_field(name="Hedef", value=f"<@{target_id}>", inline=True)
                if reason:
                    embed.add_field(name="Sebep", value=reason, inline=False)
                if message_link:
                    embed.add_field(name="Mesaj", value=f"[Jump]({message_link})", inline=False)
                await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot, db_manager))
    @tree.command(name="ban", description="Kullanıcıyı sunucudan yasaklar (Yönetici)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.checks.cooldown(1, 10.0)
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    try:
        await member.ban(reason=reason)
        await db_manager.add_forceban(member.id, interaction.guild.id, interaction.user.id, reason or "Slash Komut")
        embed = discord.Embed(title="Ban", color=0xff0000, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Hedef", value=f"{member}", inline=True)
        embed.add_field(name="Yetkili", value=f"{interaction.user}", inline=True)
        if reason: embed.add_field(name="Sebep", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)
        guild = interaction.guild
        log_channel = discord.utils.get(guild.text_channels, name="denetim-log")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Hata: {str(e)}")
        logger.error("Slash ban hatası", exc_info=e)

@tree.command(name="kick", description="Kullanıcıyı sunucudan atar (Yönetici)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(title="Kick", color=0xffaa00, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Hedef", value=f"{member}", inline=True)
        embed.add_field(name="Yetkili", value=f"{interaction.user}", inline=True)
        if reason: embed.add_field(name="Sebep", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)
        log_channel = discord.utils.get(interaction.guild.text_channels, name="denetim-log")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Hata: {str(e)}")
        logger.error("Slash kick hatası", exc_info=e)

@tree.command(name="mute", description="Kullanıcıyı susturur (Yönetici)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_mute(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not role:
        role = await interaction.guild.create_role(name="Muted")
        for ch in interaction.guild.channels:
            await ch.set_permissions(role, send_messages=False)
    try:
        await member.add_roles(role)
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(db_manager.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO mutes (user_id, guild_id, muted_by, mute_reason, mute_date) VALUES (?, ?, ?, ?, ?)",
                (member.id, interaction.guild.id, interaction.user.id, reason, now)
            )
            await db.commit()
        embed = discord.Embed(title="Mute", color=0x5555ff, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Hedef", value=f"{member}", inline=True)
        embed.add_field(name="Yetkili", value=f"{interaction.user}", inline=True)
        if reason: embed.add_field(name="Sebep", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)
        log_channel = discord.utils.get(interaction.guild.text_channels, name="denetim-log")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Hata: {str(e)}")
        logger.error("Slash mute hatası", exc_info=e)

@tree.command(name="unmute", description="Kullanıcının susturmasını kaldırır (Yönetici)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    try:
        await member.remove_roles(role)
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(db_manager.db_path) as db:
            await db.execute(
                "UPDATE mutes SET unmute_date=? WHERE user_id=? AND guild_id=?",
                (now, member.id, interaction.guild.id)
            )
            await db.commit()
        embed = discord.Embed(title="Unmute", color=0x00ff00, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Hedef", value=f"{member}", inline=True)
        embed.add_field(name="Yetkili", value=f"{interaction.user}", inline=True)
        await interaction.response.send_message(embed=embed)
        log_channel = discord.utils.get(interaction.guild.text_channels, name="denetim-log")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Hata: {str(e)}")
        logger.error("Slash unmute hatası", exc_info=e)

@tree.command(name="giverol", description="Kullanıcıya rol verir (Yönetici)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_giverol(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        embed = discord.Embed(title="Rol Verildi", color=0x00ffff, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Hedef", value=f"{member}", inline=True)
        embed.add_field(name="Yetkili", value=f"{interaction.user}", inline=True)
        embed.add_field(name="Rol", value=f"{role.name}", inline=False)
        await interaction.response.send_message(embed=embed)
        log_channel = discord.utils.get(interaction.guild.text_channels, name="denetim-log")
        if log_channel:
            await log_channel.send(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Hata: {str(e)}")
        logger.error("Slash giverol hatası", exc_info=e)

@bot.check
async def forceban_check(ctx):
    if await db_manager.is_forcebanned(ctx.author.id, ctx.guild.id):
        await ctx.send("Sen bu sunucuda forcebanlısın!")
        return False
    return True

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if await db_manager.is_forcebanned(message.author.id, message.guild.id):
        try:
            await message.delete()
        except:
            pass
        return
    await bot.process_commands(message)

bot.loop.create_task(setup(bot))
bot.run(TOKEN)

