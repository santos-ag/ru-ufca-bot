"""Testes para AutoMenuUpdater - Orquestrador de atualização automática."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.bot.auto_updater import AutoMenuUpdater
from src.scraper.menu_url_scraper import MenuPdfLink, MenuUrlScraperError
from src.scraper.pdf_downloader import PDFDownloadError


@pytest.fixture
def mock_cache():
    """Fixture: Mock do MenuCache."""
    cache = Mock()
    cache.save_menu = Mock()
    return cache


@pytest.fixture
def auto_updater(mock_cache):
    """Fixture: Instância do AutoMenuUpdater com cache mockado."""
    return AutoMenuUpdater(mock_cache)


class TestAutoMenuUpdater:
    """Testes do AutoMenuUpdater."""

    def test_initialization(self, auto_updater):
        """Deve inicializar com cache."""
        assert auto_updater.cache is not None
        assert auto_updater.scraper is not None
        assert auto_updater.downloader is not None

    @pytest.mark.asyncio
    async def test_update_menu_from_web_success(self, auto_updater, mock_cache):
        """Deve executar pipeline completo com sucesso."""
        # Simula PDF válido
        pdf_bytes = b"%PDF-1.4\n" + b"x" * 1000

        # Simula Link encontrado
        pdf_link = MenuPdfLink(
            titulo="Test",
            url="http://test.com/pdf",
            data_atualizacao="2026-03-16",
        )

        # Simula menus extraídos
        weekly_menus = {
            "2026-03-16": {
                "almoco": {"prato_principal": "Frango"},
                "janta": {"prato_principal": "Peixe"},
            }
        }

        with patch.object(auto_updater.scraper, "get_latest_pdf", new_callable=AsyncMock) as mock_scrape:
            with patch.object(auto_updater.downloader, "download", new_callable=AsyncMock) as mock_download:
                with patch("src.bot.auto_updater.PDFParser") as mock_parser_class:
                    with patch("src.bot.auto_updater.TableMenuExtractor") as mock_extractor_class:

                        # Setup mocks
                        mock_scrape.return_value = pdf_link
                        mock_download.return_value = pdf_bytes

                        # Mock parser
                        mock_parser = Mock()
                        mock_parser.extract_tables.return_value = [["table", "data"]]
                        mock_parser_class.return_value = mock_parser

                        # Mock extractor
                        mock_extractor = Mock()
                        mock_extractor.extract_menus.return_value = weekly_menus
                        mock_extractor_class.return_value = mock_extractor

                        # Executa
                        result = await auto_updater.update_menu_from_web()

                        # Validações
                        assert result is True
                        mock_scrape.assert_called_once()
                        mock_download.assert_called_once()
                        # Valida que salvou no cache
                        assert mock_cache.save_menu.call_count == len(weekly_menus)

    @pytest.mark.asyncio
    async def test_update_menu_from_web_scraper_error(self, auto_updater):
        """Deve retornar False em erro de scraping."""
        with patch.object(
            auto_updater.scraper, "get_latest_pdf", new_callable=AsyncMock
        ) as mock_scrape:
            mock_scrape.side_effect = MenuUrlScraperError("Erro de conexão")

            result = await auto_updater.update_menu_from_web()

            assert result is False

    @pytest.mark.asyncio
    async def test_update_menu_from_web_download_error(self, auto_updater):
        """Deve retornar False em erro de download."""
        pdf_link = MenuPdfLink("Test", "http://test.com", "2026-03-16")

        with patch.object(auto_updater.scraper, "get_latest_pdf", new_callable=AsyncMock) as mock_scrape:
            with patch.object(
                auto_updater.downloader, "download", new_callable=AsyncMock
            ) as mock_download:
                mock_scrape.return_value = pdf_link
                mock_download.side_effect = PDFDownloadError("Erro no download")

                result = await auto_updater.update_menu_from_web()

                assert result is False

    @pytest.mark.asyncio
    async def test_update_menu_from_web_parse_error(self, auto_updater):
        """Deve retornar False em erro de parse."""
        pdf_bytes = b"invalid"
        pdf_link = MenuPdfLink("Test", "http://test.com", "2026-03-16")

        with patch.object(auto_updater.scraper, "get_latest_pdf", new_callable=AsyncMock) as mock_scrape:
            with patch.object(auto_updater.downloader, "download", new_callable=AsyncMock) as mock_download:
                with patch("src.bot.auto_updater.PDFParser") as mock_parser_class:
                    mock_scrape.return_value = pdf_link
                    mock_download.return_value = pdf_bytes
                    mock_parser_class.side_effect = Exception("Parse error")

                    result = await auto_updater.update_menu_from_web()

                    assert result is False

    @pytest.mark.asyncio
    async def test_update_menu_from_web_empty_extraction(self, auto_updater):
        """Deve retornar False se nenhum cardápio foi extraído."""
        pdf_bytes = b"%PDF-1.4\n" + b"x" * 1000
        pdf_link = MenuPdfLink("Test", "http://test.com", "2026-03-16")

        with patch.object(auto_updater.scraper, "get_latest_pdf", new_callable=AsyncMock) as mock_scrape:
            with patch.object(auto_updater.downloader, "download", new_callable=AsyncMock) as mock_download:
                with patch("src.bot.auto_updater.PDFParser") as mock_parser_class:
                    with patch("src.bot.auto_updater.MenuExtractor") as mock_fallback_extractor:
                        mock_scrape.return_value = pdf_link
                        mock_download.return_value = pdf_bytes

                        # Parser retorna vazio
                        mock_parser = Mock()
                        mock_parser.extract_tables.return_value = None
                        mock_parser.extract_text.return_value = "some text"
                        mock_parser_class.return_value = mock_parser

                        # Fallback extractor também retorna vazio
                        mock_extractor = Mock()
                        mock_extractor.extract_menus.return_value = {}
                        mock_fallback_extractor.return_value = mock_extractor

                        result = await auto_updater.update_menu_from_web()

                        assert result is False

    @pytest.mark.asyncio
    async def test_update_menu_temp_file_cleanup(self, auto_updater):
        """Deve limpar arquivo temporário após uso."""
        pdf_bytes = b"%PDF-1.4\n" + b"x" * 1000
        pdf_link = MenuPdfLink("Test", "http://test.com", "2026-03-16")
        weekly_menus = {"2026-03-16": {"almoco": {"prato_principal": "Test"}}}

        with patch.object(auto_updater.scraper, "get_latest_pdf", new_callable=AsyncMock) as mock_scrape:
            with patch.object(auto_updater.downloader, "download", new_callable=AsyncMock) as mock_download:
                with patch("src.bot.auto_updater.PDFParser") as mock_parser_class:
                    with patch("src.bot.auto_updater.TableMenuExtractor") as mock_extractor_class:
                        with patch("src.bot.auto_updater.os.unlink") as mock_unlink:
                            mock_scrape.return_value = pdf_link
                            mock_download.return_value = pdf_bytes

                            mock_parser = Mock()
                            mock_parser.extract_tables.return_value = [["data"]]
                            mock_parser_class.return_value = mock_parser

                            mock_extractor = Mock()
                            mock_extractor.extract_menus.return_value = weekly_menus
                            mock_extractor_class.return_value = mock_extractor

                            await auto_updater.update_menu_from_web()

                            # Valida que tentou limpar o arquivo
                            mock_unlink.assert_called_once()
