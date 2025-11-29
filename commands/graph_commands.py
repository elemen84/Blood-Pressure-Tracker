# commands/graph_commands.py

import discord
from discord.ext import commands
from datetime import timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import numpy as np

from db import load_data
from utils import get_local_time, logger


class GraphCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slot_display = {'morning': 'Morning', 'afternoon': 'Afternoon', 'night': 'Night'}
        self.slot_short = {'morning': 'm', 'afternoon': 'a', 'night': 'n'}
        self.color_sys = '#FF6B6B'
        self.color_dia = '#4ECDC4'
        self.reference_color = '#FF4444'  # Color rojo para las líneas de referencia

    # --- GENERAL GRAPH (N DAYS) ---
    @commands.command(name='graph', help='Shows blood pressure trend for last N days. Usage: !graph <days>')
    async def daily_graph(self, ctx, days: int = 30):
        df = load_data()

        if df.empty:
            await ctx.send("📊 No records to generate a graph.")
            return

        cutoff_date = get_local_time() - timedelta(days=days)
        cutoff_date_np = np.datetime64(cutoff_date)

        df_filtered = df[df['day'] >= cutoff_date_np].copy()

        if df_filtered.empty:
            await ctx.send(f"📊 No records in the last {days} days.")
            return

        try:
            # CALCULAR PROMEDIOS DIARIOS
            df_daily = df_filtered.groupby('day')[['systolic', 'diastolic']].mean().reset_index()
            df_daily = df_daily.sort_values('day')

            fig, ax = plt.subplots(figsize=(12, 6))

            # Plot promedios diarios en lugar de datos individuales
            ax.plot(df_daily['day'], df_daily['systolic'], marker='o', linestyle='-',
                    label='Systolic', alpha=0.8, color=self.color_sys, linewidth=2.5, markersize=6)
            ax.plot(df_daily['day'], df_daily['diastolic'], marker='s', linestyle='-',
                    label='Diastolic', alpha=0.8, color=self.color_dia, linewidth=2.5, markersize=6)

            # AÑADIR LÍNEAS DE REFERENCIA
            ax.axhline(y=140, color=self.reference_color, linestyle='--', alpha=0.7, linewidth=1)
            ax.axhline(y=90, color=self.reference_color, linestyle='--', alpha=0.7, linewidth=1)

            # Format x-axis
            date_format = mdates.DateFormatter('%d %b')
            ax.xaxis.set_major_formatter(date_format)

            # Ajustar intervalo basado en número de días
            if days <= 7:
                interval = 1
            elif days <= 30:
                interval = 3
            else:
                interval = max(1, days // 15)

            ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))

            ax.set_title(f'Blood Pressure Trend - Last {days} Days (Daily Averages)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Pressure (mmHg)')
            ax.legend()
            ax.grid(False)  # Grid desactivado
            ax.tick_params(axis='x', rotation=45)

            plt.tight_layout()
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close(fig)

            await ctx.send(
                f"📈 **Blood Pressure Trend - Last {days} Days**\n"
                f"Showing daily averages ({len(df_daily)} days with data)",
                file=discord.File(buffer, filename=f"bp_graph_{days}days.png")
            )

        except Exception as e:
            await ctx.send("❌ Error generating graph.")
            logger.error(f"Error generating graph: {e}")

    # --- SLOT-SPECIFIC GRAPH (N DAYS) HANDLERS ---
    @commands.command(name='graph_m', help='Morning blood pressure trend for last N days. Usage: !graph_m <days>',
                      hidden=True)
    async def morning_graph_days(self, ctx, days: int = 30):
        await self._generate_slot_graph_days(ctx, 'morning', days)

    @commands.command(name='graph_a', help='Afternoon blood pressure trend for last N days. Usage: !graph_a <days>',
                      hidden=True)
    async def afternoon_graph_days(self, ctx, days: int = 30):
        await self._generate_slot_graph_days(ctx, 'afternoon', days)

    @commands.command(name='graph_n', help='Night blood pressure trend for last N days. Usage: !graph_n <days>',
                      hidden=True)
    async def night_graph_days(self, ctx, days: int = 30):
        await self._generate_slot_graph_days(ctx, 'night', days)

    # --- SLOT-SPECIFIC GRAPH (N DAYS) HELPER ---
    async def _generate_slot_graph_days(self, ctx, slot: str, days: int):
        df = load_data()

        if df.empty:
            await ctx.send("📊 No records.")
            return

        cutoff_date = get_local_time() - timedelta(days=days)
        cutoff_date_np = np.datetime64(cutoff_date)
        df_filtered = df[df['day'] >= cutoff_date_np].copy()
        df_slot = df_filtered[df_filtered['time_slot'] == slot].copy()

        if df_slot.empty:
            await ctx.send(f"📊 No **{self.slot_display[slot]}** records in the last {days} days.")
            return

        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # Para gráficos específicos por slot, mostramos los datos individuales
            ax.plot(df_slot['day'], df_slot['systolic'], marker='o', linestyle='-',
                    label='Systolic', alpha=0.8, color=self.color_sys, linewidth=2.5, markersize=6)
            ax.plot(df_slot['day'], df_slot['diastolic'], marker='s', linestyle='-',
                    label='Diastolic', alpha=0.8, color=self.color_dia, linewidth=2.5, markersize=6)

            # AÑADIR LÍNEAS DE REFERENCIA
            ax.axhline(y=140, color=self.reference_color, linestyle='--', alpha=0.7, linewidth=1)
            ax.axhline(y=90, color=self.reference_color, linestyle='--', alpha=0.7, linewidth=1)

            ax.set_title(f"Blood Pressure - {self.slot_display[slot]} Slot ({days} Days)", fontsize=14,
                         fontweight='bold')
            ax.set_xlabel("Date")
            ax.set_ylabel("Pressure (mmHg)")
            ax.legend()
            ax.grid(False)  # Grid desactivado
            ax.tick_params(axis='x', rotation=45)

            date_format = mdates.DateFormatter('%d %b')
            ax.xaxis.set_major_formatter(date_format)
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))

            plt.tight_layout()
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150)
            buffer.seek(0)
            plt.close(fig)

            await ctx.send(
                f"📈 **{self.slot_display[slot]} Blood Pressure - Last {days} Days**\n"
                f"Showing individual readings",
                file=discord.File(buffer, filename=f"bp_{self.slot_short[slot]}_{days}days.png")
            )

        except Exception as e:
            await ctx.send(f"❌ Error generating {slot} graph.")
            logger.error(f"Error generating {slot} graph: {e}")

    # --- PERIOD GRAPH HANDLERS (MONTH/YEAR) ---
    @commands.command(name='graph_month', help='Monthly blood pressure graph. Usage: !graph_month <MM-YY>')
    async def monthly_graph(self, ctx, month_str: str):
        await self._generate_period_graph(ctx, 'month', month_str)

    @commands.command(name='graph_month_m', help='Monthly morning blood pressure graph. Usage: !graph_month_m <MM-YY>',
                      hidden=True)
    async def monthly_morning_graph(self, ctx, month_str: str):
        await self._generate_period_graph(ctx, 'month', month_str, 'morning')

    @commands.command(name='graph_month_a',
                      help='Monthly afternoon blood pressure graph. Usage: !graph_month_a <MM-YY>', hidden=True)
    async def monthly_afternoon_graph(self, ctx, month_str: str):
        await self._generate_period_graph(ctx, 'month', month_str, 'afternoon')

    @commands.command(name='graph_month_n', help='Monthly night blood pressure graph. Usage: !graph_month_n <MM-YY>',
                      hidden=True)
    async def monthly_night_graph(self, ctx, month_str: str):
        await self._generate_period_graph(ctx, 'month', month_str, 'night')

    @commands.command(name='graph_year', help='Yearly blood pressure graph. Usage: !graph_year <YY>')
    async def yearly_graph(self, ctx, year_str: str):
        await self._generate_period_graph(ctx, 'year', year_str)

    @commands.command(name='graph_year_m', help='Yearly morning blood pressure graph. Usage: !graph_year_m <YY>',
                      hidden=True)
    async def yearly_morning_graph(self, ctx, year_str: str):
        await self._generate_period_graph(ctx, 'year', year_str, 'morning')

    @commands.command(name='graph_year_a', help='Yearly afternoon blood pressure graph. Usage: !graph_year_a <YY>',
                      hidden=True)
    async def yearly_afternoon_graph(self, ctx, year_str: str):
        await self._generate_period_graph(ctx, 'year', year_str, 'afternoon')

    @commands.command(name='graph_year_n', help='Yearly night blood pressure graph. Usage: !graph_year_n <YY>',
                      hidden=True)
    async def yearly_night_graph(self, ctx, year_str: str):
        await self._generate_period_graph(ctx, 'year', year_str, 'night')

    # --- HELP COMMAND FOR GRAPH SUBCOMMANDS ---
    @commands.command(name='help_graph', help='Shows available graph commands')
    async def help_graph(self, ctx):
        """Show available graph subcommands"""
        embed = discord.Embed(
            title="📈 Graph Commands Help",
            description="Available graph commands:",
            color=0x3498db
        )

        embed.add_field(
            name="General Graphs (Last N Days)",
            value=(
                "`!graph [days]` - Daily averages (all time slots)\n"
                "`!graph_m [days]` - Morning only (individual readings)\n"
                "`!graph_a [days]` - Afternoon only (individual readings)\n"
                "`!graph_n [days]` - Night only (individual readings)\n"
            ),
            inline=False
        )

        embed.add_field(
            name="Monthly Graphs",
            value=(
                "`!graph_month <MM-YY>` - Daily averages (all time slots)\n"
                "`!graph_month_m <MM-YY>` - Morning only\n"
                "`!graph_month_a <MM-YY>` - Afternoon only\n"
                "`!graph_month_n <MM-YY>` - Night only\n"
            ),
            inline=False
        )

        embed.add_field(
            name="Yearly Graphs",
            value=(
                "`!graph_year <YY>` - Monthly averages\n"
                "`!graph_year_m <YY>` - Morning monthly averages\n"
                "`!graph_year_a <YY>` - Afternoon monthly averages\n"
                "`!graph_year_n <YY>` - Night monthly averages\n"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

    # --- PERIOD GRAPH HELPER ---
    async def _generate_period_graph(self, ctx, period_type: str, period_str: str, slot: str = None):
        """Helper function to generate period graphs (month/year)"""
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
            df_daily = df_period.groupby('day')[['systolic', 'diastolic']].mean().reset_index()

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(df_daily['day'], df_daily['systolic'], marker='o', label='Systolic',
                    color=self.color_sys, linewidth=2.5, markersize=6)
            ax.plot(df_daily['day'], df_daily['diastolic'], marker='s', label='Diastolic',
                    color=self.color_dia, linewidth=2.5, markersize=6)

            # AÑADIR LÍNEAS DE REFERENCIA
            ax.axhline(y=140, color=self.reference_color, linestyle='--', alpha=0.7, linewidth=1)
            ax.axhline(y=90, color=self.reference_color, linestyle='--', alpha=0.7, linewidth=1)

            # Title construction
            title_slot = f" - {self.slot_display[slot]}" if slot else ""
            title = f"Blood Pressure Trend{title_slot} ({title_period})"

            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel("Date")
            ax.set_ylabel("Pressure (mmHg)")
            ax.legend()
            ax.grid(False)  # Grid desactivado
            ax.tick_params(axis='x', rotation=45)

            # Format x-axis based on period
            if period_type == 'month':
                date_format = mdates.DateFormatter('%d %b')
                ax.xaxis.set_major_formatter(date_format)
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
            else:  # year
                date_format = mdates.DateFormatter('%b')
                ax.xaxis.set_major_formatter(date_format)
                ax.xaxis.set_major_locator(mdates.MonthLocator())

            plt.tight_layout()

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150)
            buffer.seek(0)
            plt.close(fig)

            period_type_display = {'month': 'Month', 'year': 'Year'}
            slot_suffix = f"_{self.slot_short[slot]}" if slot else ""
            await ctx.send(
                f"📈 **Blood Pressure - {period_type_display[period_type]} {title_period}{title_slot}**\n"
                f"Showing daily averages",
                file=discord.File(buffer, filename=f"bp_{period_type}{slot_suffix}_{period_str.replace('-', '')}.png")
            )

        except ValueError:
            if period_type == 'month':
                await ctx.send("❌ **Invalid month format.** Use `MM-YY` (e.g., 12-24)")
            else:
                await ctx.send("❌ **Invalid year format.** Use `YY` (e.g., 24)")
        except Exception as e:
            await ctx.send("❌ Error generating graph.")
            logger.error(f"Error generating {period_type} graph: {e}")


async def setup(bot):
    await bot.add_cog(GraphCommands(bot))