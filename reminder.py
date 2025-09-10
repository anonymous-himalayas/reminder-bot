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


reminders = {}

def add_reminder(user_id: int, job_id: str, message: str, remind_time: datetime.datetime, rtype: str):
    if user_id not in reminders:
        reminders[user_id] = []
    reminders[user_id].append({
        "job_id": job_id,
        "message": message,
        "time": remind_time,
        "type": rtype
    })

@bot.tree.command(name="view_reminders", description="View your active reminders")
async def view_reminders(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in reminders or len(reminders[user_id]) == 0:
        await interaction.response.send_message("You don't have any active reminders.")
        return

    lines = []
    for r in reminders[user_id]:
        when = r["time"].strftime("%B %d, %Y %H:%M")
        lines.append(f"• **{r['type']}** — {r['message']} ({when})")

    response = "\n".join(lines)
    await interaction.response.send_message(f"Your reminders:\n{response}")

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

# Specific Date Reminder
@bot.tree.command(name="remind_on_date", description="Set a reminder for a specific date")
@app_commands.describe(year="Year (e.g. 2025)", month="Month (1-12)", day="Day of the month (1-31)", hour="Hour (0-23, default=9)", minute="Minute (0-59, default=0)", message="Reminder message")
async def remind_on_date(interaction: discord.Interaction, year: int, month: int, day: int, hour: int = 9, minute: int = 0, message: str = "Reminder!"):
    try:
        remind_time = datetime.datetime(year, month, day, hour, minute)
        now = datetime.datetime.now()
        if remind_time <= now:
            await interaction.response.send_message("The specified time is in the past. Please pick a future date/time.")
            return
    except ValueError as e:
        await interaction.response.send_message(f"Invalid date: {e}")
        return

    async def send_reminder():
        channel = get_reminder_channel(interaction.guild)
        if channel:
            await channel.send(f"<@{interaction.user.id}> Reminder for {remind_time.strftime('%B %d, %Y %H:%M')}: {message}")
        else:
            await interaction.user.send(f"Reminder for {remind_time.strftime('%B %d, %Y %H:%M')}: {message}")

    scheduler.add_job(send_reminder, "date", run_date=remind_time)
    await interaction.response.send_message(f"Reminder scheduled for {remind_time.strftime('%B %d, %Y %H:%M')} in #{REMINDER_CHANNEL_NAME}.")


if __name__ == "__main__":
    bot.run(TOKEN)