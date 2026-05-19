"""
Testes para o scheduler de notificações.

Seguindo TDD: Estes testes devem FALHAR primeiro (RED), depois implementamos (GREEN).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


class TestNotificationScheduler:
    """
    Testes para a classe NotificationScheduler.
    
    Responsabilidades:
    - Agendar notificações nos horários do almoço e janta
    - Enviar broadcast de mensagens para usuários inscritos
    - Tratar erros de envio (usuário bloqueou bot)
    """
    
    @pytest.fixture
    def mock_bot(self):
        """Mock do Bot do Telegram."""
        bot = Mock()
        bot.send_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def mock_cache(self):
        """Mock do MenuCache."""
        cache = Mock()
        cache.get_menu.return_value = {
            "almoco": {
                "prato_principal": "Frango Grelhado",
                "acompanhamentos": ["Arroz", "Feijão"]
            },
            "janta": {
                "prato_principal": "Peixe Assado",
                "acompanhamentos": ["Arroz", "Feijão"]
            }
        }
        return cache
    
    @pytest.fixture
    def mock_user_manager(self):
        """Mock do UserManager."""
        user_mgr = Mock()
        user_mgr.get_all_users.return_value = [12345, 67890, 11111]
        user_mgr.remove_user = Mock()
        user_mgr.is_favorite.return_value = False
        user_mgr.get_favorites.return_value = []
        return user_mgr
    
    @pytest.fixture
    def mock_formatter(self):
        """Mock do MenuFormatter."""
        formatter = Mock()
        formatter.format_meal.return_value = "🍽️ ALMOÇO\n\n🍗 Principal: Frango Grelhado"
        return formatter
    
    def test_scheduler_initializes_with_dependencies(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Scheduler deve inicializar com dependências.
        
        Arrange: Dependências mockadas
        Act: Criar instância do scheduler
        Assert: Instância criada sem erros
        """
        from src.bot.scheduler import NotificationScheduler
        
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        
        assert scheduler is not None
        assert scheduler.bot == mock_bot
        assert scheduler.cache == mock_cache
        assert scheduler.users == mock_user_manager
        assert scheduler.formatter == mock_formatter
    
    @pytest.mark.asyncio
    async def test_send_lunch_notification_broadcasts_to_all_users(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Notificação de almoço deve ser enviada para todos os usuários.
        
        Arrange: 3 usuários inscritos
        Act: Chamar send_lunch_notification
        Assert: send_message chamado 3 vezes
        """
        from src.bot.scheduler import NotificationScheduler
        
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_lunch_notification()
        
        # Verificar que buscou cardápio de hoje
        today = datetime.now().strftime("%Y-%m-%d")
        mock_cache.get_menu.assert_called_once_with(today)
        
        # Verificar que formatou o almoço (uma vez por usuário)
        assert mock_formatter.format_meal.call_count == 3
        
        # Verificar que enviou para todos os usuários
        assert mock_bot.send_message.call_count == 3
    
    @pytest.mark.asyncio
    async def test_send_dinner_notification_broadcasts_to_all_users(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Notificação de janta deve ser enviada para todos os usuários.
        
        Arrange: 3 usuários inscritos
        Act: Chamar send_dinner_notification
        Assert: send_message chamado 3 vezes
        """
        from src.bot.scheduler import NotificationScheduler
        
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_dinner_notification()
        
        # Verificar que buscou cardápio de hoje
        today = datetime.now().strftime("%Y-%m-%d")
        mock_cache.get_menu.assert_called_once_with(today)
        
        # Verificar que formatou a janta (uma vez por usuário)
        assert mock_formatter.format_meal.call_count == 3
        
        # Verificar que enviou para todos os usuários
        assert mock_bot.send_message.call_count == 3
    
    @pytest.mark.asyncio
    async def test_notification_not_sent_if_menu_unavailable(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Não deve enviar notificação se cardápio não disponível.
        
        Arrange: Cache retorna None
        Act: Chamar send_lunch_notification
        Assert: send_message não é chamado
        """
        from src.bot.scheduler import NotificationScheduler
        
        mock_cache.get_menu.return_value = None
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_lunch_notification()
        
        # Verificar que NÃO enviou mensagens
        mock_bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handles_forbidden_error_when_user_blocks_bot(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Deve remover usuário se bloqueou o bot.
        
        Arrange: send_message lança Forbidden para um usuário
        Act: Chamar send_lunch_notification
        Assert: remove_user chamado para o usuário que bloqueou
        """
        from src.bot.scheduler import NotificationScheduler
        from telegram.error import Forbidden
        
        # Configurar send_message para falhar no segundo usuário
        async def side_effect_send(chat_id, text, parse_mode=None):
            if chat_id == 67890:
                raise Forbidden("Forbidden: bot was blocked by the user")
        
        mock_bot.send_message.side_effect = side_effect_send
        
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_lunch_notification()
        
        # Verificar que tentou enviar para todos
        assert mock_bot.send_message.call_count == 3
        
        # Verificar que removeu o usuário que bloqueou
        mock_user_manager.remove_user.assert_called_once_with(67890)
    
    @pytest.mark.asyncio
    async def test_broadcast_message_sends_to_all_users(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: broadcast_message deve enviar mensagem para todos.
        
        Arrange: Mensagem customizada
        Act: Chamar broadcast_message
        Assert: send_message chamado para cada usuário
        """
        from src.bot.scheduler import NotificationScheduler
        
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        custom_message = "Teste de broadcast"
        await scheduler.broadcast_message(custom_message)
        
        # Verificar que enviou para todos os 3 usuários
        assert mock_bot.send_message.call_count == 3
        
        # Verificar que usou a mensagem correta
        for call in mock_bot.send_message.call_args_list:
            assert call[1]['text'] == custom_message
    
    @pytest.mark.asyncio
    async def test_send_notification_uses_markdown_parse_mode(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Notificações devem usar parse_mode='Markdown'.
        
        Arrange: Scheduler configurado
        Act: Chamar send_lunch_notification
        Assert: send_message chamado com parse_mode='Markdown'
        """
        from src.bot.scheduler import NotificationScheduler
        
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_lunch_notification()
        
        # Verificar que todas as chamadas usaram Markdown
        for call in mock_bot.send_message.call_args_list:
            assert call[1].get('parse_mode') == 'Markdown'
    
    @pytest.mark.asyncio
    async def test_notification_skips_if_meal_not_in_menu(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Não envia notificação se refeição específica não está no menu.
        
        Arrange: Menu sem 'almoco'
        Act: Chamar send_lunch_notification
        Assert: Não envia mensagens
        """
        from src.bot.scheduler import NotificationScheduler
        
        mock_cache.get_menu.return_value = {"janta": {"prato_principal": "Peixe"}}
        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_lunch_notification()

        # Verificar que NÃO enviou mensagens
        mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_favorite_notification_prepends_alert(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Se prato é favorito do usuário, deve prepend alert de favorito.

        Arrange: Usuário 12345 tem "Frango Grelhado" como favorito
        Act: Chamar send_lunch_notification
        Assert: Mensagem para usuário 12345 contém alerta de favorito
        """
        from src.bot.scheduler import NotificationScheduler

        mock_user_manager.is_favorite.return_value = True
        mock_user_manager.get_all_users.return_value = [12345]

        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_lunch_notification()

        call_args = mock_bot.send_message.call_args
        assert "🌟" in call_args[1]["text"] or "favorito" in call_args[1]["text"].lower()

    @pytest.mark.asyncio
    async def test_non_favorite_notification_no_alert(self, mock_bot, mock_cache, mock_user_manager, mock_formatter):
        """
        Teste: Se prato NÃO é favorito, mensagem normal sem alerta.

        Arrange: Usuário tem favoritos diferentes do prato do dia
        Act: Chamar send_lunch_notification
        Assert: Mensagem NÃO contém alerta de favorito
        """
        from src.bot.scheduler import NotificationScheduler

        mock_user_manager.get_favorites.return_value = ["Lasanha de Soja"]
        mock_user_manager.is_favorite.return_value = False
        mock_user_manager.get_all_users.return_value = [12345]

        scheduler = NotificationScheduler(mock_bot, mock_cache, mock_user_manager, mock_formatter)
        await scheduler.send_lunch_notification()

        call_args = mock_bot.send_message.call_args
        assert "🌟" not in call_args[1]["text"]
