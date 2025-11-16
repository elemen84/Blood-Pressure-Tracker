import os

# --- CONFIGURATION ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN_TA')
# Ensure this is set as an environment variable
try:
    ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID"))
except (TypeError, ValueError):
    # Use a placeholder if not set, or ensure bot doesn't crash if used
    ALERT_CHANNEL_ID = 0

DB_NAME = 'blood_pressure.db'
TIMEZONE = 'Europe/Madrid'
LOG_FILE = 'PA.log'