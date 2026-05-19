"""
Testes para os handlers de comandos do bot.

Seguindo TDD: Estes testes devem FALHAR primeiro (RED), depois implementamos (GREEN).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


class TestBotHandlers:
    """
    Testes para a classe BotHandlers.
    
    Responsabilidades:
    - Handlers para comandos do Telegram
    - Integração com cache e formatter
    - Gerenciamento de usuários inscritos
    """
    
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
        cache.get_weekly_menu.return_value = {
            "2026-03-14": {
                "almoco": {"prato_principal": "Frango"},
                "janta": {"prato_principal": "Peixe"}
            }
        }
        return cache
    
    @pytest.fixture
    def mock_user_manager(self):
        """Mock do UserManager."""
        user_mgr = Mock()
        user_mgr.add_user.return_value = True
        user_mgr.remove_user.return_value = True
        user_mgr.is_subscribed.return_value = False
        return user_mgr
    
    @pytest.fixture
    def mock_formatter(self):
        """Mock do MenuFormatter."""
        formatter = Mock()
        formatter.format_meal.return_value = "🍽️ ALMOÇO\n\n🍗 Principal: Frango Grelhado"
        formatter.format_full_menu.return_value = "📅 Cardápio de 14/03 (Sex)\n\n🍽️ ALMOÇO..."
        return formatter
    
    @pytest.fixture
    def mock_update(self):
        """Mock do Update do Telegram."""
        update = Mock()
        update.effective_user.id = 12345
        update.effective_user.first_name = "João"
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Mock do CallbackContext do Telegram."""
        context = Mock()
        return context
    
    @pytest.mark.asyncio
    async def test_start_command_replies_with_welcome(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /start deve responder com mensagem de boas-vindas.
        
        Arrange: Handler configurado com mocks
        Act: Chamar comando /start
        Assert: reply_text chamado com mensagem de boas-vindas
        """
        from src.bot.handlers import BotHandlers
        
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Bem-vindo" in call_args or "bem-vindo" in call_args
    
    @pytest.mark.asyncio
    async def test_start_command_subscribes_user(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /start deve inscrever usuário automaticamente.
        
        Arrange: Usuário não inscrito
        Act: Chamar /start
        Assert: add_user chamado com user_id correto
        """
        from src.bot.handlers import BotHandlers
        
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.start_command(mock_update, mock_context)
        
        mock_user_manager.add_user.assert_called_once_with(12345)
    
    @pytest.mark.asyncio
    async def test_almoco_command_shows_lunch_menu(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /almoco deve exibir cardápio do almoço de hoje.
        
        Arrange: Cache com cardápio disponível
        Act: Chamar /almoco
        Assert: Exibe cardápio formatado do almoço
        """
        from src.bot.handlers import BotHandlers
        
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.almoco_command(mock_update, mock_context)
        
        # Verificar que buscou cardápio de hoje
        today = datetime.now().strftime("%Y-%m-%d")
        mock_cache.get_menu.assert_called_once_with(today)
        
        # Verificar que formatou o almoço
        mock_formatter.format_meal.assert_called_once()
        
        # Verificar que enviou mensagem
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_janta_command_shows_dinner_menu(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /janta deve exibir cardápio da janta de hoje.
        
        Arrange: Cache com cardápio disponível
        Act: Chamar /janta
        Assert: Exibe cardápio formatado da janta
        """
        from src.bot.handlers import BotHandlers
        
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.janta_command(mock_update, mock_context)
        
        # Verificar que buscou cardápio de hoje
        today = datetime.now().strftime("%Y-%m-%d")
        mock_cache.get_menu.assert_called_once_with(today)
        
        # Verificar que formatou a janta
        mock_formatter.format_meal.assert_called_once()
        
        # Verificar que enviou mensagem
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_almoco_command_handles_menu_not_found(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /almoco deve lidar com cardápio não disponível.
        
        Arrange: Cache retorna None
        Act: Chamar /almoco
        Assert: Exibe mensagem de cardápio indisponível
        """
        from src.bot.handlers import BotHandlers
        
        mock_cache.get_menu.return_value = None
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.almoco_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "não disponível" in call_args.lower() or "indisponível" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_semana_command_shows_weekly_menu(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /semana deve exibir cardápio da semana.
        
        Arrange: Cache com cardápios da semana
        Act: Chamar /semana
        Assert: Exibe cardápios formatados
        """
        from src.bot.handlers import BotHandlers
        
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.semana_command(mock_update, mock_context)
        
        # Verificar que buscou cardápio semanal
        mock_cache.get_weekly_menu.assert_called_once()
        
        # Verificar que enviou mensagem
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parar_command_unsubscribes_user(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /parar deve remover usuário das notificações.
        
        Arrange: Usuário inscrito
        Act: Chamar /parar
        Assert: remove_user chamado com user_id correto
        """
        from src.bot.handlers import BotHandlers
        
        mock_user_manager.is_subscribed.return_value = True
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.parar_command(mock_update, mock_context)
        
        mock_user_manager.remove_user.assert_called_once_with(12345)
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parar_command_handles_not_subscribed(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /parar deve informar se usuário não está inscrito.
        
        Arrange: Usuário não inscrito
        Act: Chamar /parar
        Assert: Informa que usuário não está inscrito
        """
        from src.bot.handlers import BotHandlers
        
        mock_user_manager.is_subscribed.return_value = False
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.parar_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "não está inscrito" in call_args.lower() or "não inscrito" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_help_command_shows_command_list(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: /help deve listar comandos disponíveis.
        
        Arrange: Handler configurado
        Act: Chamar /help
        Assert: Lista comandos /start, /almoco, /janta, etc.
        """
        from src.bot.handlers import BotHandlers
        
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        # Verificar que contém os principais comandos
        assert "/start" in call_args
        assert "/almoco" in call_args or "/almoço" in call_args
        assert "/janta" in call_args
    
    @pytest.mark.asyncio
    async def test_handlers_use_markdown_parse_mode(self, mock_cache, mock_user_manager, mock_formatter, mock_update, mock_context):
        """
        Teste: Handlers devem usar parse_mode='Markdown' nas respostas.
        
        Arrange: Handler configurado
        Act: Chamar comando /almoco
        Assert: reply_text chamado com parse_mode='Markdown'
        """
        from src.bot.handlers import BotHandlers
        
        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        await handlers.almoco_command(mock_update, mock_context)
        
        # Verificar que parse_mode foi especificado
        call_kwargs = mock_update.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "Markdown"


class TestPdfUploadHandler:
    """
    Testes para o handler de upload de PDF pelo admin.

    Verifica que apenas o admin pode enviar PDFs, que o arquivo é processado
    corretamente pelo MenuExtractor e que o resultado é salvo no cache.
    """

    @pytest.fixture
    def mock_cache(self):
        return Mock()

    @pytest.fixture
    def mock_user_manager(self):
        return Mock()

    @pytest.fixture
    def mock_formatter(self):
        return Mock()

    @pytest.fixture
    def mock_update_admin(self):
        """Mock de Update enviado pelo admin com um documento PDF."""
        update = Mock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        doc = Mock()
        doc.file_name = "cardapio.pdf"
        doc.mime_type = "application/pdf"
        update.message.document = doc
        return update

    @pytest.fixture
    def mock_update_non_admin(self):
        """Mock de Update enviado por usuário comum."""
        update = Mock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        doc = Mock()
        doc.file_name = "cardapio.pdf"
        doc.mime_type = "application/pdf"
        update.message.document = doc
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock()

    @pytest.mark.asyncio
    async def test_pdf_upload_rejected_for_non_admin(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_update_non_admin, mock_context
    ):
        """
        Teste: Upload de PDF deve ser rejeitado para usuários não-admin.

        Arrange: ADMIN_CHAT_ID=999, usuário com id=12345
        Act: Chamar pdf_upload_handler
        Assert: reply_text com mensagem de acesso negado, cache não alterado
        """
        from src.bot.handlers import BotHandlers

        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
            await handlers.pdf_upload_handler(mock_update_non_admin, mock_context)

        mock_update_non_admin.message.reply_text.assert_called_once()
        call_args = mock_update_non_admin.message.reply_text.call_args[0][0]
        assert "permissão" in call_args.lower() or "acesso" in call_args.lower() or "admin" in call_args.lower()
        mock_cache.save_menu.assert_not_called()

    @pytest.mark.asyncio
    async def test_pdf_upload_rejected_if_not_pdf(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_update_admin, mock_context
    ):
        """
        Teste: Upload deve ser rejeitado se o arquivo não for PDF.

        Arrange: Admin envia arquivo .txt
        Act: Chamar pdf_upload_handler
        Assert: reply_text com mensagem de formato inválido
        """
        from src.bot.handlers import BotHandlers

        mock_update_admin.message.document.file_name = "arquivo.txt"
        mock_update_admin.message.document.mime_type = "text/plain"

        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
        with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
            await handlers.pdf_upload_handler(mock_update_admin, mock_context)

        call_args = mock_update_admin.message.reply_text.call_args[0][0]
        assert "pdf" in call_args.lower()
        mock_cache.save_menu.assert_not_called()

    @pytest.mark.asyncio
    async def test_pdf_upload_processes_and_saves_menu(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_update_admin, mock_context
    ):
        """
        Teste: Upload de PDF válido pelo admin deve processar e salvar cardápios.

        Arrange: Admin envia PDF válido, TableMenuExtractor retorna cardápios para 3 datas
        Act: Chamar pdf_upload_handler
        Assert: cache.save_menu chamado para cada data extraída
        """
        from src.bot.handlers import BotHandlers

        weekly_menus = {
            "2026-03-09": {"almoco": {"prato_principal": "Frango"}, "janta": {}},
            "2026-03-10": {"almoco": {"prato_principal": "Peixe"}, "janta": {}},
            "2026-03-11": {"almoco": {"prato_principal": "Carne"}, "janta": {}},
        }

        mock_file = AsyncMock()
        mock_file.download_to_drive = AsyncMock()
        mock_update_admin.message.document.get_file = AsyncMock(return_value=mock_file)

        with patch("src.bot.handlers.PDFParser") as mock_parser_cls, \
             patch("src.bot.handlers.TableMenuExtractor") as mock_table_extractor_cls:
            mock_parser_cls.return_value.extract_tables.return_value = [["mock", "table"]]
            mock_table_extractor_cls.return_value.extract_menus.return_value = weekly_menus

            handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
            with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
                await handlers.pdf_upload_handler(mock_update_admin, mock_context)

        assert mock_cache.save_menu.call_count == 3

    @pytest.mark.asyncio
    async def test_pdf_upload_replies_with_success_message(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_update_admin, mock_context
    ):
        """
        Teste: Upload bem-sucedido deve responder com confirmação.

        Arrange: Admin envia PDF válido, extração retorna 5 datas
        Act: Chamar pdf_upload_handler
        Assert: reply_text contém quantidade de datas salvas
        """
        from src.bot.handlers import BotHandlers

        weekly_menus = {f"2026-03-{9+i:02d}": {"almoco": {}, "janta": {}} for i in range(5)}

        mock_file = AsyncMock()
        mock_file.download_to_drive = AsyncMock()
        mock_update_admin.message.document.get_file = AsyncMock(return_value=mock_file)

        with patch("src.bot.handlers.PDFParser") as mock_parser_cls, \
             patch("src.bot.handlers.TableMenuExtractor") as mock_table_extractor_cls:
            mock_parser_cls.return_value.extract_tables.return_value = [["mock", "table"]]
            mock_table_extractor_cls.return_value.extract_menus.return_value = weekly_menus

            handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
            with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
                await handlers.pdf_upload_handler(mock_update_admin, mock_context)

        # Última chamada ao reply_text deve ser a confirmação final
        calls = mock_update_admin.message.reply_text.call_args_list
        success_call = calls[-1][0][0]
        assert "5" in success_call

    @pytest.mark.asyncio
    async def test_pdf_upload_replies_with_error_on_extraction_failure(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_update_admin, mock_context
    ):
        """
        Teste: Falha na extração deve responder com mensagem de erro.

        Arrange: TableMenuExtractor lança exceção
        Act: Chamar pdf_upload_handler
        Assert: reply_text com mensagem de erro, cache não alterado
        """
        from src.bot.handlers import BotHandlers

        mock_file = AsyncMock()
        mock_file.download_to_drive = AsyncMock()
        mock_update_admin.message.document.get_file = AsyncMock(return_value=mock_file)

        with patch("src.bot.handlers.PDFParser") as mock_parser_cls, \
             patch("src.bot.handlers.TableMenuExtractor") as mock_table_extractor_cls:
            mock_parser_cls.return_value.extract_tables.return_value = [["mock", "table"]]
            mock_table_extractor_cls.return_value.extract_menus.side_effect = Exception("PDF corrompido")

            handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter)
            with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
                await handlers.pdf_upload_handler(mock_update_admin, mock_context)

        calls = mock_update_admin.message.reply_text.call_args_list
        error_call = calls[-1][0][0]
        assert "erro" in error_call.lower() or "falha" in error_call.lower()
        mock_cache.save_menu.assert_not_called()


class TestAtualizarCommand:
    """
    Testes para o comando /atualizar — força atualização do cardápio via web.
    """

    @pytest.fixture
    def mock_cache(self):
        cache = Mock()
        cache.get_menu.return_value = {
            "almoco": {"prato_principal": "Frango"},
            "janta": {"prato_principal": "Peixe"},
        }
        return cache

    @pytest.fixture
    def mock_user_manager(self):
        return Mock()

    @pytest.fixture
    def mock_formatter(self):
        return Mock()

    @pytest.fixture
    def mock_auto_updater(self):
        updater = Mock()
        updater.update_menu_from_web = AsyncMock(return_value=True)
        return updater

    @pytest.fixture
    def mock_update_admin(self):
        update = Mock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_update_non_admin(self):
        update = Mock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock()

    @pytest.mark.asyncio
    async def test_atualizar_success_admin(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_auto_updater, mock_update_admin, mock_context
    ):
        """
        Teste: Admin executa /atualizar e recebe confirmação de sucesso.
        """
        from src.bot.handlers import BotHandlers

        mock_cache.get_menu.return_value = {"almoco": {"prato_principal": "Frango"}}

        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter, mock_auto_updater)
        with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
            await handlers.atualizar_command(mock_update_admin, mock_context)

        mock_auto_updater.update_menu_from_web.assert_called_once()
        calls = mock_update_admin.message.reply_text.call_args_list
        success_call = calls[-1][0][0]
        assert "atualizado" in success_call.lower() or "sucesso" in success_call.lower()

    @pytest.mark.asyncio
    async def test_atualizar_rejected_non_admin(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_auto_updater, mock_update_non_admin, mock_context
    ):
        """
        Teste: Usuário não-admin deve ser rejeitado.
        """
        from src.bot.handlers import BotHandlers

        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter, mock_auto_updater)
        with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
            await handlers.atualizar_command(mock_update_non_admin, mock_context)

        mock_auto_updater.update_menu_from_web.assert_not_called()
        mock_update_non_admin.message.reply_text.assert_called_once()
        call_args = mock_update_non_admin.message.reply_text.call_args[0][0]
        assert "admin" in call_args.lower() or "permissão" in call_args.lower()

    @pytest.mark.asyncio
    async def test_atualizar_failure(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_auto_updater, mock_update_admin, mock_context
    ):
        """
        Teste: Quando a atualização falha, deve informar o admin.
        """
        from src.bot.handlers import BotHandlers

        mock_auto_updater.update_menu_from_web = AsyncMock(return_value=False)

        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter, mock_auto_updater)
        with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
            await handlers.atualizar_command(mock_update_admin, mock_context)

        calls = mock_update_admin.message.reply_text.call_args_list
        error_call = calls[-1][0][0]
        assert "falha" in error_call.lower() or "erro" in error_call.lower()

    @pytest.mark.asyncio
    async def test_atualizar_no_auto_updater_configured(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_update_admin, mock_context
    ):
        """
        Teste: Quando auto_updater é None, deve informar erro.
        """
        from src.bot.handlers import BotHandlers

        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter, auto_updater=None)
        with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
            await handlers.atualizar_command(mock_update_admin, mock_context)

        mock_update_admin.message.reply_text.assert_called_once()
        call_args = mock_update_admin.message.reply_text.call_args[0][0]
        assert "não está configurada" in call_args.lower() or "configurada" in call_args.lower()

    @pytest.mark.asyncio
    async def test_atualizar_success_no_menu_for_today(
        self, mock_cache, mock_user_manager, mock_formatter,
        mock_auto_updater, mock_update_admin, mock_context
    ):
        """
        Teste: Atualização bem-sucedida mas sem cardápio para hoje.
        """
        from src.bot.handlers import BotHandlers

        mock_cache.get_menu.return_value = None

        handlers = BotHandlers(mock_cache, mock_user_manager, mock_formatter, mock_auto_updater)
        with patch.dict("os.environ", {"ADMIN_CHAT_ID": "999"}):
            await handlers.atualizar_command(mock_update_admin, mock_context)

        calls = mock_update_admin.message.reply_text.call_args_list
        success_call = calls[-1][0][0]
        assert "semana" in success_call.lower()
