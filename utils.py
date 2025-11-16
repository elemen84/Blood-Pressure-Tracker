import logging
from datetime import datetime
import pytz
from config import TIMEZONE, LOG_FILE

# --- LOGGING SETUP ---
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')
logger = logging.getLogger('BloodPressureBot')

def get_local_time():
    """Gets current time in configured timezone, falling back to system time if pytz is missing."""
    try:
        # Intenta usar pytz para obtener la hora con zona horaria
        import pytz

        # 1. Obtener la zona horaria
        tz = pytz.timezone(TIMEZONE)

        # 2. Obtener la hora localizada y quitar la info de zona horaria (naive)
        # para compatibilidad con SQLite/Pandas.
        return datetime.now(tz).replace(tzinfo=None)

    except ImportError:
        # Si pytz no está instalado (la importación falla)
        logger.warning("⚠️ pytz not installed. Using system time. Install: pip install pytz")
        return datetime.now()

    except Exception as e:
        # Si la zona horaria es inválida u ocurre cualquier otro error
        logger.warning(f"⚠️ Timezone error {TIMEZONE}: {e}. Using system time.")
        return datetime.now()


# Need to import sys to check for pytz
import sys