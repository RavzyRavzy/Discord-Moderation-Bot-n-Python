import discord
from discord.ext import commands, tasks
from collections import defaultdict
from datetime import datetime, timezone, timedelta

class RaidProtect(commands.Cog):
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.action_cache = defaultdict(list)
        self.threshold = 5  # Süre içinde bu kadar işlemi yaparsa alarm
        self.time_window = 10  # saniye

    async def get_log_channel(self, guild: discord.Guild):
        channel = discord.utils.get(guild.text_channels, name="denetim-log")
        if not channel:
            overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=True)}
            channel = await guild.create_text_channel("denetim-log", overwrites=overwrites)
        return channel

    async def log_raid(self, guild, user, action, count):
        channel = await self.get_log_channel(guild)
        embed = discord.Embed(
            title="Raid Koruma Alarmı",
            description=f"{user} {action} işlemi hızlı şekilde yaptı!",
            color=0xff0000,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Kullanıcı", value=f"{user} ({user.id})")
        embed.add_field(name="İşlem Sayısı", value=str(count))
        await channel.send(embed=embed)

    async def check_raid(self, user, action_type):
        now = datetime.utcnow()
        self.action_cache[(user.id, action_type)] = [
            t for t in self.action_cache[(user.id, action_type)]
            if now - t < timedelta(seconds=self.time_window)
        ]
        self.action_cache[(user.id, action_type)].append(now)
        if len(self.action_cache[(user.id, action_type)]) >= self.threshold:
            return True
        return False

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                if not entry.user.guild_permissions.administrator:
                    if await self.check_raid(entry.user, "KICK"):
                        await self.log_raid(guild, entry.user, "kick", len(self.action_cache[(entry.user.id, "KICK")]))
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == member.id:
                if not entry.user.guild_permissions.administrator:
                    if await self.check_raid(entry.user, "BAN"):
                        await self.log_raid(guild, entry.user, "ban", len(self.action_cache[(entry.user.id, "BAN")]))
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.role_delete):
            if not entry.user.guild_permissions.administrator:
                if await self.check_raid(entry.user, "ROLE_DELETE"):
                    await self.log_raid(guild, entry.user, "rol silme", len(self.action_cache[(entry.user.id, "ROLE_DELETE")]))

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.role_create):
            if not entry.user.guild_permissions.administrator:
                if await self.check_raid(entry.user, "ROLE_CREATE"):
                    await self.log_raid(guild, entry.user, "rol oluşturma", len(self.action_cache[(entry.user.id, "ROLE_CREATE")]))

async def setup(bot):
    from main import db_manager
    await bot.add_cog(RaidProtect(bot, db_manager))
