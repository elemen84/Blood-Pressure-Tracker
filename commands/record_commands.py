# commands/record_commands.py

import discord
from discord.ext import commands
from datetime import datetime
import asyncio
import io
import pandas as pd

from db import save_data, load_data, delete_last_record, get_record, update_data
from utils import get_local_time, logger


class RecordCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slot_map = {'m': 'morning', 'a': 'afternoon', 'n': 'night'}
        self.slot_display = {'m': 'Morning', 'a': 'Afternoon', 'n': 'Night', 'morning': 'Morning',
                             'afternoon': 'Afternoon', 'night': 'Night'}

    # --- REGISTRATION COMMAND ---
    @commands.command(name='register',
                      help='Registers blood pressure. Usage: !register <systolic> <diastolic> <time_slot> [dd-mm-yy]')
    async def register_bp(self, ctx, systolic: int, diastolic: int, slot: str, *date):
        try:
            slot = slot.lower()
            if slot not in self.slot_map:
                await ctx.send("❌ **Invalid time slot.** Use `m` (morning), `a` (afternoon), or `n` (night).")
                return

            if not (50 <= systolic <= 250) or not (30 <= diastolic <= 150):
                await ctx.send("❌ **Values out of range.** Systolic: 50-250, Diastolic: 30-150")
                return

            day = get_local_time()  # Default to current time

            if date:
                date_str = " ".join(date)
                try:
                    # Permitir fechas con un solo dígito (ej: 2-11-25 en lugar de 02-11-25)
                    day = self._parse_flexible_date(date_str)
                except ValueError:
                    await ctx.send("❌ **Invalid date format.** Use `dd-mm-yy` (e.g., 25-12-24 or 2-12-24)")
                    return

            full_slot = self.slot_map[slot]
            success = save_data(day, full_slot, systolic, diastolic)

            if not success:
                await ctx.send("❌ **Error saving record.** Please try again.")
                return

            # Value evaluation
            if systolic >= 180 or diastolic >= 120:
                evaluation = "🚨 **HYPERTENSIVE CRISIS!** Seek immediate medical attention."
            elif systolic >= 160 or diastolic >= 100:
                evaluation = "⚠️ **STAGE 2 HYPERTENSION!** Consult your doctor urgently."
            elif systolic >= 140 or diastolic >= 90:
                evaluation = "🟠 **STAGE 1 HYPERTENSION.** Pay attention the coming days."
            elif systolic >= 135 and diastolic > 85:
                evaluation = "🟡 **ELEVATED.** Monitor and apply lifestyle changes."
            elif systolic < 90 or diastolic < 60:
                evaluation = "ℹ️ **HYPOTENSION.** Check if you have symptoms."
            elif systolic < 80 or diastolic < 50:
                evaluation = "⚠️ **HYPOTENSION.** Seek medical attention."
            else:
                evaluation = "✅ **NORMAL/OPTIMAL.** Good work."

            await ctx.send(
                f"✅ **Record Saved:**\n"
                f"📅 Day: **{day.strftime('%d-%m-%y')}**\n"
                f"⏰ Time Slot: **{self.slot_display[slot]}**\n"
                f"💓 Blood Pressure: **{systolic}/{diastolic}** mmHg\n"
                f"{evaluation}"
            )
        except Exception as e:
            await ctx.send(f"❌ **Unexpected error:** {e}")
            logger.error(f"Error in register command: {e}")

    def _parse_flexible_date(self, date_str):
        """Parse dates with flexible formatting (allows single-digit days/months)"""
        try:
            # Primero intentar con el formato estándar
            return datetime.strptime(date_str, '%d-%m-%y')
        except ValueError:
            # Si falla, intentar con formato flexible
            parts = date_str.split('-')
            if len(parts) == 3:
                day, month, year = parts
                # Añadir ceros a la izquierda si es necesario
                day = day.zfill(2)
                month = month.zfill(2)
                # Asegurar formato de año de 2 dígitos
                if len(year) == 2:
                    year = year
                elif len(year) == 4:
                    year = year[2:]
                else:
                    raise ValueError("Invalid year format")

                normalized_date = f"{day}-{month}-{year}"
                return datetime.strptime(normalized_date, '%d-%m-%y')
            else:
                raise ValueError("Invalid date format")

    # --- SHOW LAST RECORDS ---
    @commands.command(name='last', help='Show last records. Usage: !last [count]')
    async def show_last(self, ctx, count: int = 5):
        df = load_data()

        if df.empty:
            await ctx.send("📝 No records.")
            return

        # Sort by record_date (timestamp) for true last record order
        df_last = df.sort_values('record_date', ascending=True).head(count)
        df_last['day_str'] = df_last['day'].dt.strftime('%d/%m/%y')

        if df_last.empty:
            await ctx.send("📝 No records found.")
            return

        output = [f"📝 **Last {len(df_last)} records:**\n"]
        for index, row in df_last.iterrows():
            slot_short = {'morning': 'm', 'afternoon': 'a', 'night': 'n'}
            slot_s = slot_short.get(row['time_slot'], '?')

            # Mostrar información de fecha y hora en lugar de ID
            record_time = pd.to_datetime(row['record_date']).strftime('%H:%M')
            output.append(
                f"• **{row['day_str']}** ({slot_s}): **{row['systolic']}/{row['diastolic']}** mmHg"
            )

        await ctx.send('\n'.join(output))

    # --- EDIT COMMAND ---
    @commands.command(name='edit', help='Edits a record. Usage: !edit <systolic> <diastolic> <slot> <dd-mm-yy>')
    async def edit_bp(self, ctx, systolic: int, diastolic: int, slot: str, date_str: str):
        try:
            slot = slot.lower()
            if slot not in self.slot_map:
                await ctx.send("❌ **Invalid time slot.** Use `m` (morning), `a` (afternoon), or `n` (night).")
                return

            if not (50 <= systolic <= 250) or not (30 <= diastolic <= 150):
                await ctx.send("❌ **Values out of range.** Systolic: 50-250, Diastolic: 30-150")
                return

            try:
                # Usar el parser flexible de fechas
                parsed_date = self._parse_flexible_date(date_str)
                day_str = parsed_date.strftime('%d-%m-%y')  # Normalizar a formato estándar
            except ValueError:
                await ctx.send("❌ **Invalid date format.** Use `dd-mm-yy` (e.g., 25-12-24 or 2-12-24).")
                return

            full_slot = self.slot_map[slot]
            old_record = get_record(day_str, full_slot)

            if not old_record:
                await ctx.send(
                    f"❌ **Record not found.** No record exists for date **{day_str}** in time slot **{self.slot_display[slot]}**.")
                return

            old_sys, old_dia = old_record

            confirm_message = (
                f"⚠️ **CONFIRMATION REQUIRED** ⚠️\n"
                f"Are you sure you want to **EDIT** this record?\n"
                f"**Current Record:** {day_str} ({slot}): **{old_sys}/{old_dia}** mmHg\n"
                f"**New Values:** {day_str} ({slot}): **{systolic}/{diastolic}** mmHg\n"
                f"React with ✅ to confirm the edit. (30 seconds)"
            )

            msg = await ctx.send(confirm_message)
            await msg.add_reaction('✅')

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message.id == msg.id

            try:
                await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("❌ Timeout expired. Record was **NOT** edited.")
                return

            if update_data(day_str, full_slot, systolic, diastolic):
                await ctx.send(
                    f"✅ **RECORD SUCCESSFULLY EDITED**\n"
                    f"📅 Day: **{day_str}**\n"
                    f"⏰ Time Slot: **{self.slot_display[slot]}**\n"
                    f"🔄 Changed from **{old_sys}/{old_dia}** to **{systolic}/{diastolic}** mmHg."
                )
            else:
                await ctx.send("❌ Error updating record.")

        except Exception as e:
            await ctx.send(f"❌ **Unexpected error:** {e}")
            logger.error(f"Error in edit command: {e}")

    # --- DELETE COMMAND ---
    @commands.command(name='delete', help='Deletes the last recorded blood pressure entry.')
    async def delete_last_command(self, ctx):
        df = load_data()
        if df.empty:
            await ctx.send("❌ **No records found** to delete.")
            return

        # Get the actual last record by record_date
        last_record = df.sort_values('record_date', ascending=True).iloc[0]

        slot_short = {'morning': 'm', 'afternoon': 'a', 'night': 'n'}
        slot_s = slot_short.get(last_record['time_slot'], '?')

        confirm_message = (
            f"⚠️ **CONFIRMATION REQUIRED** ⚠️\n"
            f"Are you sure you want to **DELETE** your **LAST** record?\n"
            f"**Record to delete:** {last_record['day'].strftime('%d-%m-%y')} ({slot_s}): **{last_record['systolic']}/{last_record['diastolic']}** mmHg\n"
            f"React with ✅ to confirm deletion. (30 seconds)"
        )

        msg = await ctx.send(confirm_message)
        await msg.add_reaction('✅')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message.id == msg.id

        try:
            await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("❌ Timeout expired. Record was **NOT** deleted.")
            return

        if delete_last_record():
            await ctx.send(
                f"🗑️ **SUCCESSFULLY DELETED** the last record:\n"
                f"{last_record['day'].strftime('%d-%m-%y')} ({slot_s}): **{last_record['systolic']}/{last_record['diastolic']}** mmHg"
            )
        else:
            await ctx.send("❌ Error trying to delete record. Please try again.")

    # --- EXPORT COMMAND ---
    @commands.command(name='export', help='Export data to CSV. Usage: !export')
    async def export_data(self, ctx):
        df = load_data()

        if df.empty:
            await ctx.send("📁 No data to export.")
            return

        try:
            export_df = df.copy()
            export_df['Date'] = export_df['day'].dt.strftime('%d-%m-%y')
            export_df['Time_of_Record'] = pd.to_datetime(export_df['record_date']).dt.strftime('%H:%M:%S')

            # Map full slot names to short codes
            slot_map_short = {'morning': 'm', 'afternoon': 'a', 'night': 'n'}
            export_df['Time_Slot'] = export_df['time_slot'].map(slot_map_short)

            export_df = export_df[['Date', 'Time_Slot', 'systolic', 'diastolic', 'Time_of_Record']]
            export_df.columns = ['Date', 'Time_Slot', 'Systolic', 'Diastolic', 'Time_of_Record']

            buffer = io.StringIO()
            export_df.to_csv(buffer, index=False)
            buffer.seek(0)

            file = discord.File(
                io.BytesIO(buffer.getvalue().encode('utf-8')),
                filename=f"blood_pressure_export_{datetime.now().strftime('%Y%m%d')}.csv"
            )

            await ctx.send(
                f"📁 **Data Export**\n"
                f"📊 Records: **{len(export_df)}**\n"
                f"📅 Period: **{export_df['Date'].min()}** to **{export_df['Date'].max()}**",
                file=file
            )

            logger.info("📁 Data exported")

        except Exception as e:
            await ctx.send("❌ Error exporting data. Check logs for details.")
            logger.error(f"Error exporting data: {e}")


async def setup(bot):
    await bot.add_cog(RecordCommands(bot))