import discord
from discord.ext import commands
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

REMINDER_CHANNEL_NAME = "reminder-announcements"
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

print()
print(f"TOKEN: {TOKEN}")
print()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    scheduler.start()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Sync error: {e}")

def get_reminder_channel(guild: discord.Guild):
    """Find the reminder channel by name."""
    channel = discord.utils.get(guild.text_channels, name=REMINDER_CHANNEL_NAME)
    return channel

# Single Reminder
@bot.tree.command(name="remindme", description="Set a single reminder")
@app_commands.describe(time_in_minutes="How many minutes from now?", message="Reminder message")
async def remindme(interaction: discord.Interaction, time_in_minutes: int, message: str):
    remind_time = datetime.datetime.now() + datetime.timedelta(minutes=time_in_minutes)

    async def send_reminder():
        channel = get_reminder_channel(interaction.guild)
        if channel:
            await channel.send(f"<@{interaction.user.id}> Reminder: {message}")
        else:
            await interaction.user.send(f"Reminder (no channel found): {message}")

    scheduler.add_job(send_reminder, "date", run_date=remind_time)
    await interaction.response.send_message(f"Reminder set for {time_in_minutes} minutes from now in #{REMINDER_CHANNEL_NAME}.")

# Recurring Every X Days
@bot.tree.command(name="remind_every_x_days", description="Set a recurring reminder every X days")
@app_commands.describe(days="How often in days?", message="Reminder message")
async def remind_every_x_days(interaction: discord.Interaction, days: int, message: str):
    async def send_reminder():
        channel = get_reminder_channel(interaction.guild)
        if channel:
            await channel.send(f"<@{interaction.user.id}> Reminder (every {days} days): {message}")
        else:
            await interaction.user.send(f"Reminder (every {days} days, no channel found): {message}")

    scheduler.add_job(send_reminder, IntervalTrigger(days=days))
    await interaction.response.send_message(f"Recurring reminder set every {days} days in #{REMINDER_CHANNEL_NAME}.")

# Recurring Weekly 
@bot.tree.command(name="remind_weekly", description="Set a weekly reminder")
@app_commands.describe(weekday="Day of the week (e.g., Tuesday)", hour="Hour (0-23)", minute="Minute (0-59)", message="Reminder message")
async def remind_weekly(interaction: discord.Interaction, weekday: str, hour: int, minute: int, message: str):
    days_map = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun"
    }
    weekday = weekday.lower()
    if weekday not in days_map:
        await interaction.response.send_message("Invalid weekday. Try: Monday, Tuesday, etc.")
        return

    async def send_reminder():
        channel = get_reminder_channel(interaction.guild)
        if channel:
            await channel.send(f"<@{interaction.user.id}> Weekly Reminder ({weekday.title()} at {hour:02d}:{minute:02d}): {message}")
        else:
            await interaction.user.send(f"Weekly Reminder (no channel found): {message}")

    scheduler.add_job(send_reminder, CronTrigger(day_of_week=days_map[weekday], hour=hour, minute=minute))
    await interaction.response.send_message(f"Weekly reminder set for every {weekday.title()} at {hour:02d}:{minute:02d} in #{REMINDER_CHANNEL_NAME}.")

bot.run(TOKEN)