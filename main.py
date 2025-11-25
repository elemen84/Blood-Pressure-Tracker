import sys
import blood_pressure_bot

def main():
    """Initializes the database, sets up scheduled tasks, and runs the Discord bot."""

    # Manejar token faltante
    if not blood_pressure_bot.DISCORD_TOKEN:
        print("❌ ERROR: Discord token not found.")
        print("Please set the DISCORD_TOKEN_TA environment variable.")
        sys.exit(1)

    try:
        print("🚀 Starting Blood Pressure Bot...")

        # 1. Inicializar DB (Llamando a la función del módulo)
        print("📊 Initializing database...")
        blood_pressure_bot.setup_db()

        # 2. Imprimir configuración y correr el bot
        print(f"🌍 Timezone configured: {blood_pressure_bot.TIMEZONE}")
        print("🔔 Starting scheduled tasks...")

        # Ejecutamos el bot con el objeto bot del módulo
        blood_pressure_bot.bot.run(blood_pressure_bot.DISCORD_TOKEN)

    except blood_pressure_bot.discord.LoginFailure:
        print("❌ ERROR: Invalid Discord token.")
        blood_pressure_bot.logger.critical("❌ Invalid Discord token.")
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user.")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        blood_pressure_bot.logger.critical(f"Critical error: {e}")


if __name__ == '__main__':
    main()