# blood_pressure_bot.py

import discord
from discord.ext import commands, tasks
from datetime import timedelta
import asyncio

# Local Imports (Usando importaciones absolutas correctas)
from config import DISCORD_TOKEN, ALERT_CHANNEL_ID, DB_NAME, TIMEZONE
from utils import logger, get_local_time
from db import setup_db, load_data, backup_database
from commands.record_commands import RecordCommands
from commands.graph_commands import GraphCommands
from commands.data_commands import DataCommands

# External libs for Alert Task
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io


# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# --- EVENTS ---
@bot.event
async def on_ready():
    """Event when bot logs in"""
    setup_db()
    print(f'🤖 Blood Pressure Bot connected as {bot.user}')
    print(f'📊 Database initialized: {DB_NAME}')
    print(f'⚡ Command prefix: {bot.command_prefix}')
    print(f'🌍 Timezone: {TIMEZONE}')

    # Load Cogs
    try:
        await bot.add_cog(RecordCommands(bot))
        await bot.add_cog(GraphCommands(bot))
        await bot.add_cog(DataCommands(bot))
        logger.info("✅ All command modules loaded.")
    except Exception as e:
        logger.critical(f"❌ Failed to load command modules: {e}")

    # Start Tasks
    if not daily_alert.is_running():
        daily_alert.start()
        print(f'🔔 Daily alert task started.')

    if not backup_task.is_running():
        backup_task.start()
        print(f'💾 Backup task started.')


@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ **Missing arguments.** Use `!help {ctx.command}` for correct syntax.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ **Invalid argument.** Please check the input types (numbers for BP, date format, etc).")
    elif isinstance(error, commands.CommandNotFound):
        pass # Ignore unknown commands silently
    else:
        await ctx.send(f"❌ **Unexpected error:** {error}")
        logger.error(f"Error in command {ctx.command}: {error}")


# --- SCHEDULED TASKS ---
@tasks.loop(hours=24)
async def daily_alert():
    """Daily check of last 10 days average and send alert if needed."""
    await bot.wait_until_ready()

    target_channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not target_channel:
        logger.error(f"❌ Alert channel with ID {ALERT_CHANNEL_ID} not found. Skipping daily alert.")
        return

    logger.info("🔔 Executing daily alert...")

    df = load_data()
    if df.empty:
        logger.info("📊 No data for daily alerts")
        return

    try:
        # Calculate daily averages
        daily_avg_data = df.groupby('day')[['systolic', 'diastolic']].mean().reset_index()
        daily_avg_data = daily_avg_data.sort_values('day', ascending=False)

        # Take last 10 days with data
        last_10_days = daily_avg_data.head(10)

        if len(last_10_days) >= 5:
            avg_sys = last_10_days['systolic'].mean()
            avg_dia = last_10_days['diastolic'].mean()

            # Alert criteria (S > 135 or D > 85)
            if avg_sys > 135 or avg_dia > 85:
                # Generate graph
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(last_10_days['day'], last_10_days['systolic'], marker='o', label='Systolic', color='#FF6B6B',
                        linewidth=2.5, markersize=6)
                ax.plot(last_10_days['day'], last_10_days['diastolic'], marker='s', label='Diastolic', color='#4ECDC4',
                        linewidth=2.5, markersize=6)

                ax.set_title(f'10-Day Blood Pressure Trend - ALERT', fontsize=14, fontweight='bold')
                ax.set_xlabel('Date')
                ax.set_ylabel('Pressure (mmHg)')
                ax.legend()
                ax.grid(False)
                ax.tick_params(axis='x', rotation=45)

                # Format x-axis
                date_format = mdates.DateFormatter('%d %b')
                ax.xaxis.set_major_formatter(date_format)
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))

                plt.tight_layout()

                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                buffer.seek(0)
                plt.close(fig)

                await target_channel.send(
                    f"⚠️ **BLOOD PRESSURE ALERT** ⚠️\n\n"
                    f"Your average over the last {len(last_10_days)} days is: **{avg_sys:.1f}/{avg_dia:.1f}** mmHg\n\n",
                    file=discord.File(buffer, filename="bp_alert.png")
                )
                logger.info("✅ Alert sent")
            else:
                logger.info(f"✅ Daily average {avg_sys:.1f}/{avg_dia:.1f} is within target. No alert sent.")
        else:
            logger.info("Less than 5 days of data, skipping alert.")

        logger.info("🔔 Daily alerts completed")

    except Exception as e:
        logger.error(f"❌ Critical error in daily alert task: {e}")


@daily_alert.before_loop
async def before_daily_alert():
    """Ensures the task starts at 8:00 AM local time."""
    await bot.wait_until_ready()

    now = get_local_time()
    next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)

    if now >= next_run:
        next_run += timedelta(days=1)

    wait_seconds = (next_run - now).total_seconds()
    logger.info(f"🔔 Daily alert waiting {wait_seconds:.0f} seconds to align with 8:00 AM {TIMEZONE}.")

    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)


@tasks.loop(hours=24)
async def backup_task():
    """Creates daily database backup."""
    try:
        await bot.wait_until_ready()
        # Sleep for a bit after startup to avoid conflict with initial DB access
        await asyncio.sleep(3600)

        backup_name = backup_database()
        if backup_name:
            logger.info(f"💾 Automatic backup created: {backup_name}")
    except Exception as e:
        logger.error(f"❌ Error in automatic backup task: {e}")

# --- EL BLOQUE if __name__ == '__main__': DEBE ELIMINARSE DE AQUÍ ---