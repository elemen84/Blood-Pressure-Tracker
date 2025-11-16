import sqlite3
import pandas as pd
from datetime import datetime
import shutil
import os
from config import DB_NAME
from utils import logger, get_local_time


# --- DATABASE FUNCTIONS ---
def setup_db():
    """Initializes the database structure."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT,
                time_slot TEXT,
                systolic INTEGER,
                diastolic INTEGER,
                record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")


def load_data():
    """Loads all data into DataFrame."""
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM records ORDER BY day, record_date", conn)
        conn.close()

        if not df.empty:
            # Convert 'day' column from 'dd-mm-yy' string format to datetime object
            df['day'] = pd.to_datetime(df['day'], format='%d-%m-%y', errors='coerce')
            df = df.dropna(subset=['day'])
            df[['systolic', 'diastolic']] = df[['systolic', 'diastolic']].apply(pd.to_numeric)

            # Ensure record_date is in datetime format for sorting/filtering
            df['record_date'] = pd.to_datetime(df['record_date'])

        logger.info(f"📊 Data loaded - Records: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()


def save_data(day, slot, sys, dia):
    """Saves a new record."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Ensure day is saved as 'dd-mm-yy' string
        cursor.execute(
            "INSERT INTO records (day, time_slot, systolic, diastolic) VALUES (?, ?, ?, ?)",
            (day.strftime('%d-%m-%y'), slot, sys, dia))
        conn.commit()
        conn.close()
        logger.info(f"💾 Record saved - Date: {day.strftime('%d-%m-%y')}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving record: {e}")
        return False


def update_data(day_str, slot, sys, dia):
    """Updates an existing record based on day and time_slot."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE records SET systolic = ?, diastolic = ?, record_date = CURRENT_TIMESTAMP "
            "WHERE day = ? AND time_slot = ?",
            (sys, dia, day_str, slot)
        )
        conn.commit()
        conn.close()
        logger.info(f"✏️ Record updated - Day: {day_str}, Slot: {slot}")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating record: {e}")
        return False


def get_record(day_str, slot):
    """Retrieves a single record based on day (str) and time_slot."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT systolic, diastolic FROM records WHERE day = ? AND time_slot = ?",
            (day_str, slot)
        )
        record = cursor.fetchone()
        conn.close()
        return record
    except Exception as e:
        logger.error(f"❌ Error retrieving record: {e}")
        return None



import sqlite3


def delete_last_record():
    """Deletes the record with the latest record_date timestamp."""

    # Asume que DB_NAME y logger están disponibles

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Consulta: Borra el registro cuya record_date sea la más alta (el más reciente).
        sql_query = """
            DELETE FROM records 
            WHERE record_date = (SELECT MAX(record_date) FROM records)
        """

        cursor.execute(sql_query)
        conn.commit()

        if cursor.rowcount > 0:
            logger.info("🗑️ Last record deleted")
            return True
        else:
            logger.warning("⚠️ No record found to delete.")
            return False

    except Exception as e:
        logger.error(f"❌ Error deleting record: {e}")
        return False

    finally:
        # Asegura que la conexión se cierra en todos los casos
        if 'conn' in locals() and conn:
            conn.close()


def backup_database():
    """Creates database backup."""
    try:
        if not os.path.exists('backup'):
            os.makedirs('backup')

        backup_name = os.path.join('backup', f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_NAME, backup_name)

        # Clean old backups (keep last 7)
        try:
            backup_files = [f for f in os.listdir('backup') if f.startswith('backup_') and f.endswith('.db')]
            if len(backup_files) > 7:
                # Sort by creation time to find the oldest
                backup_files.sort(key=lambda x: os.path.getctime(os.path.join('backup', x)))
                for old_backup in backup_files[:-7]:
                    os.remove(os.path.join('backup', old_backup))
                    logger.info(f"🧹 Old backup deleted: {old_backup}")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Could not clean old backups: {cleanup_error}")

        logger.info(f"💾 Backup created: {backup_name}")
        return backup_name

    except Exception as e:
        logger.error(f"❌ Error creating backup: {e}")
        return None