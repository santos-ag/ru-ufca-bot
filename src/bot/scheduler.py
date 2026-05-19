"""Broadcast de notificações automáticas de cardápio."""

from datetime import datetime
import logging
from telegram.error import Forbidden, TelegramError

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Envia cardápios para todos os inscritos nos horários configurados."""
    
    def __init__(self, bot, menu_cache, user_manager, formatter):
        self.bot = bot
        self.cache = menu_cache
        self.users = user_manager
        self.formatter = formatter
    
    async def _send_meal_notification(self, meal_key: str, meal_type: str, meal_name: str):
        """Formata e faz o broadcast de uma refeição. Pula se não houver cardápio."""
        today = datetime.now().strftime("%Y-%m-%d")
        menu_data = self.cache.get_menu(today)
        
        if not menu_data or meal_key not in menu_data:
            logger.info(f"{meal_name} menu not available for {today}, skipping notification")
            return
        
        meal = menu_data[meal_key]
        prato_principal = meal.get("prato_principal", "")
        
        user_ids = self.users.get_all_users()
        for user_id in user_ids:
            try:
                formatted_message = self.formatter.format_meal(meal, meal_type)
                
                if prato_principal and self.users.is_favorite(user_id, prato_principal):
                    formatted_message = (
                        f"🌟 *ALERTA DE FAVORITO!* 🌟\n\n"
                        f"_{prato_principal}_ está no cardápio de hoje!\n\n"
                        + formatted_message
                    )
                
                await self.bot.send_message(
                    chat_id=user_id,
                    text=formatted_message,
                    parse_mode="Markdown"
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
