"""Entry point do RU UFCA Bot."""

import os
import logging
from datetime import time

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.bot.formatter import MenuFormatter
from src.bot.handlers import BotHandlers
from src.bot.scheduler import NotificationScheduler
from src.bot.auto_updater import AutoMenuUpdater
from src.cache.menu_cache import MenuCache, UserManager

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_bot() -> Application:
    """Monta a aplicação: instancia componentes, registra handlers e retorna pronto pra rodar."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN não configurado nas variáveis de ambiente")

    cache = MenuCache("data/menu_cache.json")
    users = UserManager("data/users.json")
    formatter = MenuFormatter()
    handlers = BotHandlers(cache, users, formatter)

    app = Application.builder().token(token).build()

    # Scheduler precisa do bot da aplicação
    scheduler = NotificationScheduler(app.bot, cache, users, formatter)
    
    # Auto updater para atualização automática de cardápios
    auto_updater = AutoMenuUpdater(cache)

    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("almoco", handlers.almoco_command))
    app.add_handler(CommandHandler("janta", handlers.janta_command))
    app.add_handler(CommandHandler("semana", handlers.semana_command))
    app.add_handler(CommandHandler("parar", handlers.parar_command))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(MessageHandler(filters.Document.PDF, handlers.pdf_upload_handler))

    setup_scheduler(app, scheduler, auto_updater)

    logger.info("Bot configurado com sucesso.")
    return app


def setup_scheduler(app: Application, scheduler: NotificationScheduler, auto_updater: AutoMenuUpdater) -> None:
    """Registra os jobs de notificação e atualização automática no job_queue."""
    tz_name = os.environ.get("TIMEZONE", "America/Fortaleza")
    lunch_time_str = os.environ.get("LUNCH_NOTIFICATION_TIME", "10:30")
    dinner_time_str = os.environ.get("DINNER_NOTIFICATION_TIME", "16:30")

    lunch_h, lunch_m = map(int, lunch_time_str.split(":"))
    dinner_h, dinner_m = map(int, dinner_time_str.split(":"))

    app.job_queue.run_daily(
        callback=lambda ctx: scheduler.send_lunch_notification(),
        time=time(lunch_h, lunch_m, tzinfo=_get_timezone(tz_name)),
        name="lunch_notification",
    )

    app.job_queue.run_daily(
        callback=lambda ctx: scheduler.send_dinner_notification(),
        time=time(dinner_h, dinner_m, tzinfo=_get_timezone(tz_name)),
        name="dinner_notification",
    )

    # Job semanal: segunda-feira às 09:00
    app.job_queue.run_weekly(
        callback=lambda ctx: auto_updater.update_menu_from_web(),
        day=0,  # 0 = Monday (0=Seg, 1=Ter, ..., 6=Dom)
        time=time(9, 0, tzinfo=_get_timezone(tz_name)),
        name="weekly_menu_update",
    )

    logger.info(
        f"Scheduler configurado: almoço {lunch_time_str}, janta {dinner_time_str} ({tz_name})"
    )
    logger.info("Auto-update semanal configurado: segunda-feira às 09:00")


def _get_timezone(tz_name: str):
    """Resolve o nome do timezone; cai pra UTC se não encontrar."""
    try:
        import zoneinfo
        return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        logger.warning(f"Timezone '{tz_name}' não encontrado, usando UTC")
        import datetime
        return datetime.timezone.utc


def main() -> None:
    """Inicia o bot em modo polling."""
    logger.info("Iniciando RU UFCA Bot...")
    app = create_bot()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
