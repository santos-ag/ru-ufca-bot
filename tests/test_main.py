"""
Testes para o entry point da aplicação.

Seguindo TDD: Estes testes devem FALHAR primeiro (RED), depois implementamos (GREEN).

O main.py é responsável por:
- Carregar configurações do ambiente (.env)
- Instanciar e conectar todos os módulos
- Registrar handlers no bot do Telegram
- Iniciar o APScheduler com os horários configurados
- Iniciar o polling do bot
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestBotFactory:
    """
    Testes para a função create_bot que monta a aplicação.

    Verifica que os componentes são instanciados e conectados corretamente.
    """

    @patch("src.main.Application")
    @patch("src.main.MenuCache")
    @patch("src.main.UserManager")
    @patch("src.main.MenuFormatter")
    @patch("src.main.BotHandlers")
    @patch("src.main.NotificationScheduler")
    def test_create_bot_returns_application(
        self, mock_sched, mock_handlers, mock_fmt, mock_users, mock_cache, mock_app_cls
    ):
        """
        Teste: create_bot deve retornar uma Application do telegram.

        Arrange: Token válido via patch de env
        Act: Chamar create_bot
        Assert: Retorno é um objeto Application
        """
        from telegram.ext import Application
        from src.main import create_bot

        mock_app = MagicMock(spec=Application)
        mock_app_cls.builder.return_value.token.return_value.build.return_value = mock_app

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "fake:TOKEN"}):
            app = create_bot()

        assert app is not None
        assert isinstance(app, Application)

    @patch("src.main.MenuCache")
    @patch("src.main.UserManager")
    @patch("src.main.MenuFormatter")
    @patch("src.main.BotHandlers")
    @patch("src.main.NotificationScheduler")
    def test_create_bot_raises_without_token(
        self, mock_sched, mock_handlers, mock_fmt, mock_users, mock_cache
    ):
        """
        Teste: create_bot deve levantar erro se token não configurado.

        Arrange: Sem TELEGRAM_BOT_TOKEN no ambiente
        Act: Chamar create_bot
        Assert: Levanta ValueError
        """
        import os
        from src.main import create_bot

        env = {k: v for k, v in os.environ.items() if k != "TELEGRAM_BOT_TOKEN"}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
                create_bot()

    @patch("src.main.Application")
    @patch("src.main.MenuCache")
    @patch("src.main.UserManager")
    @patch("src.main.MenuFormatter")
    @patch("src.main.BotHandlers")
    @patch("src.main.NotificationScheduler")
    def test_create_bot_registers_start_handler(
        self, mock_sched, mock_handlers, mock_fmt, mock_users, mock_cache, mock_app_cls
    ):
        """
        Teste: create_bot deve registrar handler para /start.

        Arrange: Token válido
        Act: Chamar create_bot
        Assert: app.add_handler foi chamado com um CommandHandler para /start
        """
        from src.main import create_bot
        from telegram.ext import Application, CommandHandler

        mock_app = MagicMock(spec=Application)
        mock_app_cls.builder.return_value.token.return_value.build.return_value = mock_app

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "fake:TOKEN"}):
            create_bot()

        # Verificar que add_handler foi chamado com um CommandHandler para "start"
        added_handlers = [
            call.args[0]
            for call in mock_app.add_handler.call_args_list
            if isinstance(call.args[0], CommandHandler)
        ]
        start_commands = [cmd for h in added_handlers for cmd in h.commands]
        assert "start" in start_commands

    @patch("src.main.Application")
    @patch("src.main.MenuCache")
    @patch("src.main.UserManager")
    @patch("src.main.MenuFormatter")
    @patch("src.main.BotHandlers")
    @patch("src.main.NotificationScheduler")
    def test_create_bot_registers_all_commands(
        self, mock_sched, mock_handlers, mock_fmt, mock_users, mock_cache, mock_app_cls
    ):
        """
        Teste: create_bot deve registrar todos os comandos do bot.

        Arrange: Token válido
        Act: Chamar create_bot
        Assert: Handlers para /almoco, /janta, /semana, /parar, /help registrados
        """
        from src.main import create_bot
        from telegram.ext import Application, CommandHandler

        mock_app = MagicMock(spec=Application)
        mock_app_cls.builder.return_value.token.return_value.build.return_value = mock_app

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "fake:TOKEN"}):
            create_bot()

        added_handlers = [
            call.args[0]
            for call in mock_app.add_handler.call_args_list
            if isinstance(call.args[0], CommandHandler)
        ]
        registered = {cmd for h in added_handlers for cmd in h.commands}

        assert "start" in registered
        assert "almoco" in registered
        assert "janta" in registered
        assert "semana" in registered
        assert "parar" in registered
        assert "help" in registered

    @patch("src.main.Application")
    @patch("src.main.MenuCache")
    @patch("src.main.UserManager")
    @patch("src.main.MenuFormatter")
    @patch("src.main.BotHandlers")
    @patch("src.main.NotificationScheduler")
    def test_create_bot_instantiates_all_components(
        self, mock_sched_cls, mock_handlers_cls, mock_fmt_cls, mock_users_cls, mock_cache_cls, mock_app_cls
    ):
        """
        Teste: create_bot deve instanciar todos os componentes.

        Arrange: Token válido
        Act: Chamar create_bot
        Assert: MenuCache, UserManager, MenuFormatter, BotHandlers e
                NotificationScheduler foram instanciados
        """
        from src.main import create_bot
        from telegram.ext import Application

        mock_app = MagicMock(spec=Application)
        mock_app_cls.builder.return_value.token.return_value.build.return_value = mock_app

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "fake:TOKEN"}):
            create_bot()

        mock_cache_cls.assert_called_once()
        mock_users_cls.assert_called_once()
        mock_fmt_cls.assert_called_once()
        mock_handlers_cls.assert_called_once()
        mock_sched_cls.assert_called_once()


class TestSchedulerSetup:
    """
    Testes para a função setup_scheduler que configura os jobs periódicos.
    """

    def test_setup_scheduler_adds_lunch_job(self):
        """
        Teste: setup_scheduler deve adicionar job para notificação do almoço.

        Arrange: Mocks de Application e NotificationScheduler
        Act: Chamar setup_scheduler
        Assert: Job com horário 10:30 registrado
        """
        from src.main import setup_scheduler

        mock_app = MagicMock()
        mock_scheduler = MagicMock()
        mock_auto_updater = MagicMock()

        with patch.dict("os.environ", {
            "LUNCH_NOTIFICATION_TIME": "10:30",
            "DINNER_NOTIFICATION_TIME": "16:30",
            "TIMEZONE": "America/Fortaleza",
        }):
            setup_scheduler(mock_app, mock_scheduler, mock_auto_updater)

        # Verificar que job_queue.run_daily foi chamado pelo menos 2x (almoço + janta)
        assert mock_app.job_queue.run_daily.call_count >= 2

    def test_setup_scheduler_adds_dinner_job(self):
        """
        Teste: setup_scheduler deve adicionar job para notificação da janta.

        Arrange: Mocks de Application e NotificationScheduler
        Act: Chamar setup_scheduler
        Assert: Dois jobs diários registrados (almoço e janta)
        """
        from src.main import setup_scheduler

        mock_app = MagicMock()
        mock_scheduler = MagicMock()
        mock_auto_updater = MagicMock()

        with patch.dict("os.environ", {
            "LUNCH_NOTIFICATION_TIME": "10:30",
            "DINNER_NOTIFICATION_TIME": "16:30",
            "TIMEZONE": "America/Fortaleza",
        }):
            setup_scheduler(mock_app, mock_scheduler, mock_auto_updater)

        # Exatamente 2 jobs diários: almoço e janta
        assert mock_app.job_queue.run_daily.call_count == 2
