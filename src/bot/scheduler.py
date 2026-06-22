"""Broadcast de notificações automáticas de cardápio."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from telegram.error import Forbidden, TelegramError

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Envia cardápios para todos os inscritos nos horários configurados."""

    def __init__(self, bot, menu_cache, user_manager, formatter, tz=None):
        self.bot = bot
        self.cache = menu_cache
        self.users = user_manager
        self.formatter = formatter
        self.tz = tz or ZoneInfo(os.environ.get("TIMEZONE", "America/Fortaleza"))

    async def _send_meal_notification(self, meal_key: str, meal_type: str, meal_name: str):
        """Formata e faz o broadcast de uma refeição. Pula se não houver cardápio."""
        today = datetime.now(self.tz).strftime("%Y-%m-%d")
        menu_data = self.cache.get_menu(today)

        if not menu_data or meal_key not in menu_data:
            logger.info(f"{meal_name} menu not available for {today}, skipping notification")
            return

        meal = menu_data[meal_key]
        # prato_principal pode ser string ou lista — normaliza pra lista
        raw_prato = meal.get("prato_principal", "")
        pratos = raw_prato if isinstance(raw_prato, list) else [raw_prato] if raw_prato else []

        user_ids = self.users.get_all_users()
        for user_id in user_ids:
            try:
                user_favorites = self.users.get_favorites(user_id)
                favorite_pratos = [p for p in pratos if p and self.users.is_favorite(user_id, p)]

                formatted_message, reply_markup = self.formatter.format_meal_with_keyboard(
                    meal, meal_type, "fav", favorites_list=user_favorites
                )

                if favorite_pratos:
                    fav_names = ", ".join(favorite_pratos)
                    formatted_message = (
                        f"🌟 *ALERTA DE FAVORITO!* 🌟\n\n"
                        f"_{fav_names}_ está no cardápio de hoje!\n\n"
                        + formatted_message
                    )

                await self.bot.send_message(
                    chat_id=user_id,
                    text=formatted_message,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
                logger.debug(f"Notification sent to user {user_id}")

            except Forbidden:
                self.users.remove_user(user_id)
                logger.info(f"User {user_id} blocked bot, removed from list")

            except TelegramError as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")

    async def send_lunch_notification(self):
        """Dispara a notificação do almoço (agendada para 10:30)."""
        await self._send_meal_notification("almoco", "Almoço", "Lunch")

    async def send_dinner_notification(self):
        """Dispara a notificação da janta (agendada para 16:30)."""
        await self._send_meal_notification("janta", "Jantar", "Dinner")

    async def broadcast_message(self, message: str):
        """Envia uma mensagem avulsa para todos os inscritos."""
        await self._broadcast_to_users(message)

    async def _broadcast_to_users(self, message: str):
        """Itera sobre todos os inscritos e envia a mensagem. Remove quem bloqueou o bot."""
        user_ids = self.users.get_all_users()

        for user_id in user_ids:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown"
                )
                logger.debug(f"Notification sent to user {user_id}")

            except Forbidden:
                # Usuário bloqueou o bot — tirar da lista
                self.users.remove_user(user_id)
                logger.info(f"User {user_id} blocked bot, removed from list")

            except TelegramError as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
