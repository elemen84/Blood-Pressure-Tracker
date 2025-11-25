from discord.ext import commands
from datetime import timedelta
import numpy as np
import discord
import pandas as pd

from db import load_data
from utils import get_local_time, logger


class DataCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slot_display = {'morning': 'Morning', 'afternoon': 'Afternoon', 'night': 'Night'}

    # --- N DAYS DATA TABLES ---
    @commands.command(name='data', help='Shows blood pressure data table for last N days. Usage: !data <days>')
    async def data_table(self, ctx, days: int = 30):
        await self._generate_data_table(ctx, days)

    @commands.command(name='data_m',
                      help='Shows morning blood pressure data table for last N days. Usage: !data_m <days>',
                      hidden=True)
    async def data_morning_table(self, ctx, days: int = 30):
        await self._generate_data_table(ctx, days, 'morning')

    @commands.command(name='data_a',
                      help='Shows afternoon blood pressure data table for last N days. Usage: !data_a <days>',
                      hidden=True)
    async def data_afternoon_table(self, ctx, days: int = 30):
        await self._generate_data_table(ctx, days, 'afternoon')

    @commands.command(name='data_n',
                      help='Shows night blood pressure data table for last N days. Usage: !data_n <days>', hidden=True)
    async def data_night_table(self, ctx, days: int = 30):
        await self._generate_data_table(ctx, days, 'night')

    async def _generate_data_table(self, ctx, days: int, slot: str = None):
        """Helper function to generate N-day data tables"""
        df = load_data()

        if df.empty:
            await ctx.send("📊 No records.")
            return

        cutoff_date = get_local_time() - timedelta(days=days)
        cutoff_date_np = np.datetime64(cutoff_date)
        df_period = df[df['day'] >= cutoff_date_np].copy()

        if df_period.empty:
            await ctx.send(f"📊 No records in the last {days} days.")
            return

        if slot:
            df_period = df_period[df_period['time_slot'] == slot].copy()
            if df_period.empty:
                await ctx.send(f"📊 No **{self.slot_display[slot]}** records in the last {days} days.")
                return

        # Calculate daily averages
        df_daily = df_period.groupby('day')[['systolic', 'diastolic']].mean().round(1).reset_index()
        df_daily = df_daily.sort_values('day', ascending=False)

        if df_daily.empty:
            await ctx.send(f"📊 No data to display for the last {days} days.")
            return

        # Calculate overall average
        avg_sys = df_daily['systolic'].mean().round(1)
        avg_dia = df_daily['diastolic'].mean().round(1)

        # Create table
        table_data = []
        table_data.append(f"📋 **Blood Pressure Data - Last {days} Days**")
        if slot:
            table_data.append(f"**Time Slot:** {self.slot_display[slot]}")

        table_data.append("```")
        table_data.append(f"{'Date':<12} {'Systolic':<10} {'Diastolic':<10}")
        table_data.append("-" * 35)

        for _, row in df_daily.iterrows():
            date_str = row['day'].strftime('%d-%m-%y')
            table_data.append(f"{date_str:<12} {row['systolic']:<10} {row['diastolic']:<10}")

        table_data.append("-" * 35)
        table_data.append(f"{'AVERAGE':<12} {avg_sys:<10} {avg_dia:<10}")
        table_data.append("```")

        message = '\n'.join(table_data)
        if len(message) > 2000:
            short_message = (
                f"📋 **Blood Pressure Data - Last {days} Days**\n"
                f"{'Time Slot: ' + self.slot_display[slot] if slot else ''}\n"
                f"**Overall Average:** {avg_sys}/{avg_dia} mmHg\n"
                f"**Days with data:** {len(df_daily)}"
            )
            await ctx.send(short_message)
        else:
            await ctx.send(message)

    # --- TOTAL STATISTICS COMMAND ---
    @commands.command(name='total', aliases=['stats', 'estadisticas'],
                      help='Shows monthly statistics by time slots with totals and percentages')
    async def total_stats(self, ctx):
        """Shows monthly statistics by time slots"""
        try:
            df = load_data()
            if df.empty:
                await ctx.send("📊 No blood pressure data recorded.")
                return

            # Use existing 'time_slot' column
            if 'time_slot' not in df.columns:
                await ctx.send("❌ **Error:** 'time_slot' column not found in data.")
                return

            # Convert 'day' to datetime if needed
            df['day'] = pd.to_datetime(df['day'])
            df['month'] = df['day'].dt.to_period('M')

            # Create pivot table using existing time_slot
            pivot_table = pd.pivot_table(
                df,
                values='systolic',
                index='month',
                columns='time_slot',
                aggfunc='count',
                fill_value=0
            )

            # Ensure all time slots are present
            for time_slot in ['morning', 'afternoon', 'night']:
                if time_slot not in pivot_table.columns:
                    pivot_table[time_slot] = 0

            # Reorder columns
            pivot_table = pivot_table[['morning', 'afternoon', 'night']]

            # Calculate monthly total
            pivot_table['total'] = pivot_table.sum(axis=1)

            # Sort by month (newest first)
            pivot_table = pivot_table.sort_index(ascending=False)

            # Calculate overall totals
            total_readings = pivot_table['total'].sum()
            total_morning = pivot_table['morning'].sum()
            total_afternoon = pivot_table['afternoon'].sum()
            total_night = pivot_table['night'].sum()

            # Create formatted table - ONLY PERCENTAGES IN TOTAL LINE
            table_data = []
            table_data.append("📊 **READINGS STATISTICS BY MONTH**")
            table_data.append("```")
            # Headers
            table_data.append("Month      |  Morning | Afternoon|  Night   | Total")
            table_data.append("-----------|----------|----------|----------|----------")

            for month, row in pivot_table.iterrows():
                month_str = str(month).replace('-', ' ')

                # NO percentages in monthly lines - just counts
                table_data.append(
                    f"{month_str:10} | {row['morning']:>7}  | "
                    f"{row['afternoon']:>9}| "
                    f"{row['night']:>8} | {row['total']:>5}"
                )

            table_data.append("-----------|----------|----------|----------|----------")

            # Calculate overall percentages
            morning_pct_total = (total_morning / total_readings * 100) if total_readings > 0 else 0
            afternoon_pct_total = (total_afternoon / total_readings * 100) if total_readings > 0 else 0
            night_pct_total = (total_night / total_readings * 100) if total_readings > 0 else 0

            # TOTAL line WITH percentages
            table_data.append(
                f"{'TOTAL':10} | {total_morning:>2} ({morning_pct_total:2.0f}%) | "
                f"{total_afternoon:>2} ({afternoon_pct_total:2.0f}%) | "
                f"{total_night:>2} ({night_pct_total:2.0f}%) | {total_readings:>5}"
            )
            table_data.append("```")

            # Summary
            table_data.append("**General Summary:**")
            table_data.append(f"• **Total readings recorded:** {total_readings}")
            table_data.append(
                f"• **Time slot distribution:** 🌅 Morning: {total_morning} ({morning_pct_total:.1f}%) | 🌞 Afternoon: {total_afternoon} ({afternoon_pct_total:.1f}%) | 🌙 Night: {total_night} ({night_pct_total:.1f}%)")

            message = '\n'.join(table_data)

            # Check message length
            if len(message) > 2000:
                # Short message if too long
                short_message = (
                    f"📊 **READINGS STATISTICS BY MONTH**\n"
                    f"**Total readings:** {total_readings}\n"
                    f"🌅 Morning: {total_morning} ({morning_pct_total:.1f}%)\n"
                    f"🌞 Afternoon: {total_afternoon} ({afternoon_pct_total:.1f}%)\n"
                    f"🌙 Night: {total_night} ({night_pct_total:.1f}%)"
                )
                await ctx.send(short_message)
            else:
                await ctx.send(message)

        except Exception as e:
            logger.error(f"Error in !total command: {e}", exc_info=True)
            await ctx.send("❌ **Error generating statistics.** Please try again.")


    # --- PERIOD (MONTH/YEAR) DATA TABLES ---
    @commands.command(name='data_month', help='Shows monthly blood pressure data table. Usage: !data_month <MM-YY>')
    async def data_month_table(self, ctx, month_str: str):
        await self._generate_period_data_table(ctx, 'month', month_str)

    @commands.command(name='data_month_m', help='Shows monthly morning BP data table. Usage: !data_month_m <MM-YY>',
                      hidden=True)
    async def data_month_morning_table(self, ctx, month_str: str):
        await self._generate_period_data_table(ctx, 'month', month_str, 'morning')

    @commands.command(name='data_month_a', help='Shows monthly afternoon BP data table. Usage: !data_month_a <MM-YY>',
                      hidden=True)
    async def data_month_afternoon_table(self, ctx, month_str: str):
        await self._generate_period_data_table(ctx, 'month', month_str, 'afternoon')

    @commands.command(name='data_month_n', help='Shows monthly night BP data table. Usage: !data_month_n <MM-YY>',
                      hidden=True)
    async def data_month_night_table(self, ctx, month_str: str):
        await self._generate_period_data_table(ctx, 'month', month_str, 'night')

    @commands.command(name='data_year', help='Shows yearly blood pressure data table. Usage: !data_year <YY>')
    async def data_year_table(self, ctx, year_str: str):
        await self._generate_period_data_table(ctx, 'year', year_str)

    @commands.command(name='data_year_m', help='Shows yearly morning BP data table. Usage: !data_year_m <YY>',
                      hidden=True)
    async def data_year_morning_table(self, ctx, year_str: str):
        await self._generate_period_data_table(ctx, 'year', year_str, 'morning')

    @commands.command(name='data_year_a', help='Shows yearly afternoon BP data table. Usage: !data_year_a <YY>',
                      hidden=True)
    async def data_year_afternoon_table(self, ctx, year_str: str):
        await self._generate_period_data_table(ctx, 'year', year_str, 'afternoon')

    @commands.command(name='data_year_n', help='Shows yearly night BP data table. Usage: !data_year_n <YY>',
                      hidden=True)
    async def data_year_night_table(self, ctx, year_str: str):
        await self._generate_period_data_table(ctx, 'year', year_str, 'night')

    # --- HELP COMMANDS FOR SUBCOMMANDS ---
    @commands.command(name='help_data', help='Shows available data commands')
    async def help_data(self, ctx):
        """Show available data subcommands"""
        embed = discord.Embed(
            title="📊 Data Commands Help",
            description="Available data table commands:",
            color=0x3498db
        )

        embed.add_field(
            name="General Data Tables",
            value=(
                "`!data [days]` - All time slots (default: 30 days)\n"
                "`!data_m [days]` - Morning only\n"
                "`!data_a [days]` - Afternoon only\n"
                "`!data_n [days]` - Night only\n"
            ),
            inline=False
        )

        embed.add_field(
            name="Monthly Data Tables",
            value=(
                "`!data_month <MM-YY>` - All time slots\n"
                "`!data_month_m <MM-YY>` - Morning only\n"
                "`!data_month_a <MM-YY>` - Afternoon only\n"
                "`!data_month_n <MM-YY>` - Night only\n"
            ),
            inline=False
        )

        embed.add_field(
            name="Yearly Data Tables",
            value=(
                "`!data_year <YY>` - All time slots\n"
                "`!data_year_m <YY>` - Morning only\n"
                "`!data_year_a <YY>` - Afternoon only\n"
                "`!data_year_n <YY>` - Night only\n"
            ),
            inline=False
        )

        embed.add_field(
            name="Statistics",
            value=(
                "`!total` - Estadísticas mensuales por franjas horarias\n"
                "`!stats` - Alias para !total\n"
                "`!estadisticas` - Alias en español\n"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

    # --- PERIOD DATA TABLE HELPER ---
    async def _generate_period_data_table(self, ctx, period_type: str, period_str: str, slot: str = None):
        """Helper function to generate period data tables (month/year)"""
        df = load_data()

        if df.empty:
            await ctx.send("📊 No records.")
            return

        try:
            if period_type == 'month':
                # Expecting MM-YY format
                month, year_short = period_str.split('-')
                year_full = f"20{year_short}" if len(year_short) == 2 else year_short
                period_filter = f"{year_full}-{month.zfill(2)}"
                df_period = df[df['day'].dt.strftime('%Y-%m') == period_filter].copy()
                title_period = f"{month}/{year_short}"
            else:  # year
                year_short = period_str
                year_full = f"20{year_short}" if len(year_short) == 2 else year_short
                period_filter = int(year_full)
                df_period = df[df['day'].dt.year == period_filter].copy()
                title_period = year_short

            if df_period.empty:
                await ctx.send(f"📊 No records for **{title_period}**")
                return

            if slot:
                df_period = df_period[df_period['time_slot'] == slot].copy()
                if df_period.empty:
                    await ctx.send(f"📊 No **{self.slot_display[slot]}** records for **{title_period}**")
                    return

            # Calculate daily averages
            df_daily = df_period.groupby('day')[['systolic', 'diastolic']].mean().round(1).reset_index()
            df_daily = df_daily.sort_values('day', ascending=False)

            if df_daily.empty:
                await ctx.send(f"📊 No data to display for **{title_period}**")
                return

            # Calculate overall average
            avg_sys = df_daily['systolic'].mean().round(1)
            avg_dia = df_daily['diastolic'].mean().round(1)

            # Create table
            table_data = []
            period_display = {'month': 'Month', 'year': 'Year'}
            table_data.append(f"📋 **Blood Pressure Data - {period_display[period_type]} {title_period}**")
            if slot:
                table_data.append(f"**Time Slot:** {self.slot_display[slot]}")

            table_data.append("```")
            table_data.append(f"{'Date':<12} {'Systolic':<10} {'Diastolic':<10}")
            table_data.append("-" * 35)

            for _, row in df_daily.iterrows():
                date_str = row['day'].strftime('%d-%m-%y')
                table_data.append(f"{date_str:<12} {row['systolic']:<10} {row['diastolic']:<10}")

            table_data.append("-" * 35)
            table_data.append(f"{'AVERAGE':<12} {avg_sys:<10} {avg_dia:<10}")
            table_data.append("```")

            message = '\n'.join(table_data)
            if len(message) > 2000:
                short_message = (
                    f"📋 **{period_display[period_type]} Blood Pressure Data - {title_period}**\n"
                    f"{'Time Slot: ' + self.slot_display[slot] if slot else ''}\n"
                    f"**Overall Average:** {avg_sys}/{avg_dia} mmHg\n"
                    f"**Days with data:** {len(df_daily)}"
                )
                await ctx.send(short_message)
            else:
                await ctx.send(message)

        except ValueError:
            if period_type == 'month':
                await ctx.send("❌ **Invalid month format.** Use `MM-YY` (e.g., 12-24)")
            else:
                await ctx.send("❌ **Invalid year format.** Use `YY` (e.g., 24)")
        except Exception as e:
            await ctx.send("❌ Error generating data table.")
            logger.error(f"Error generating {period_type} data table: {e}")


async def setup(bot):
    await bot.add_cog(DataCommands(bot))