import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import re
from collections import defaultdict
import asyncio

class Automod(commands.Cog):
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        self.message_cache = defaultdict(list)
        self.flood_threshold = 5  
        self.flood_time = 7  
        self.profanity_list = ["küfür1", "küfür2", "küfür3"]  
        self.link_regex = re.compile(r"https?://\S+")
        self.caps_threshold = 0.7  

    async def mute_member(self, member: discord.Member, reason="Otomatik Moderasyon"):
        role = discord.utils.get(member.guild.roles, name="Muted")
        if not role:
            role = await member.guild.create_role(name="Muted")
            for ch in member.guild.channels:
                await ch.set_permissions(role, send_messages=False)
        await member.add_roles(role)
        await self.log_action(member.guild.id, member.id, "MUTE", reason)

    async def log_action(self, guild_id, user_id, action, reason):
        guild = self.bot.get_guild(guild_id)
        if guild:
            channel = discord.utils.get(guild.text_channels, name="denetim-log")
            if channel:
                embed = discord.Embed(title=f"Otomatik Moderasyon | {action}", color=0xff0000, timestamp=datetime.now(timezone.utc))
                embed.add_field(name="Kullanıcı", value=f"<@{user_id}>", inline=True)
                embed.add_field(name="Sebep", value=reason, inline=False)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        now = datetime.utcnow().timestamp()
        self.message_cache[message.author.id] = [t for t in self.message_cache[message.author.id] if now - t < self.flood_time]
        self.message_cache[message.author.id].append(now)
        if len(self.message_cache[message.author.id]) > self.flood_threshold:
            await self.mute_member(message.author, "Flood")
            await message.channel.send(f"{message.author.mention} flood nedeniyle susturuldu!", delete_after=5)
            self.message_cache[message.author.id] = []
            return

        content_lower = message.content.lower()
        if any(bad_word in content_lower for bad_word in self.profanity_list):
            await message.delete()
            await self.mute_member(message.author, "Küfür")
            await message.channel.send(f"{message.author.mention} küfür nedeniyle susturuldu!", delete_after=5)
            return

        if self.link_regex.search(message.content):
            await message.delete()
            await self.mute_member(message.author, "Link paylaşımı")
            await message.channel.send(f"{message.author.mention} link paylaşımı nedeniyle susturuldu!", delete_after=5)
            return

        if len(message.content) >= 5:
            caps_ratio = sum(1 for c in message.content if c.isupper()) / len(message.content)
            if caps_ratio >= self.caps_threshold:
                await message.delete()
                await self.mute_member(message.author, "Caps spam")
                await message.channel.send(f"{message.author.mention} caps nedeniyle susturuldu!", delete_after=5)
                return

async def setup(bot):
    from main import db_manager
    await bot.add_cog(Automod(bot, db_manager))
