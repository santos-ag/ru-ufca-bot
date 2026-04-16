"""Testes para MenuUrlScraper - Scraper de URLs de cardápios."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.scraper.menu_url_scraper import (
    MenuUrlScraper,
    MenuPdfLink,
    MenuUrlScraperError,
    MenuUrlNotFoundError,
)


class TestMenuPdfLink:
    """Testes do Value Object MenuPdfLink."""

    def test_create_pdf_link(self):
        """Deve criar um link de PDF válido."""
        link = MenuPdfLink(
            titulo="PRAE/RU/UFCA – Cardápio 13/04/2026 a 17/04/2026",
            url="https://documentos.ufca.edu.br/?post_type=doc&p=45616",
            data_atualizacao="2026-03-16 12:00:37",
        )

        assert link.titulo == "PRAE/RU/UFCA – Cardápio 13/04/2026 a 17/04/2026"
        assert link.url == "https://documentos.ufca.edu.br/?post_type=doc&p=45616"
        assert link.data_atualizacao == "2026-03-16 12:00:37"

    def test_pdf_link_repr(self):
        """Deve ter representação legível."""
        link = MenuPdfLink(
            titulo="Test",
            url="http://test.com/pdf",
            data_atualizacao="2026-01-01",
        )

        repr_str = repr(link)
        assert "MenuPdfLink" in repr_str
        assert "Test" in repr_str


class TestMenuUrlScraper:
    """Testes do MenuUrlScraper."""

    @pytest.mark.asyncio
    async def test_scraper_initialization(self):
        """Deve inicializar com URL padrão."""
        scraper = MenuUrlScraper()
        assert scraper.url == MenuUrlScraper.DEFAULT_URL

    @pytest.mark.asyncio
    async def test_scraper_custom_url(self):
        """Deve inicializar com URL customizada."""
        custom_url = "http://custom.com/cardapios"
        scraper = MenuUrlScraper(custom_url)
        assert scraper.url == custom_url

    @pytest.mark.asyncio
    async def test_fetch_pdf_links_success(self):
        """Deve extrair URLs de PDFs com sucesso."""
        html_content = """
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>PRAE/RU/UFCA – Cardápio 13/04/2026 a 17/04/2026</div>
            <div style='font-size: 0.9em; padding-left: 1.5em;' class="content">
                <p>PRAE/RU/UFCA – Cardápio 13/04/2026 a 17/04/2026</p>
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=45616' target='_blank'><i class='arrow alternate circle down icon'></i> Baixar documento</a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-03-16 12:00:37</p>
            </div>
        </div>
        """

        scraper = MenuUrlScraper()

        with patch("src.scraper.menu_url_scraper.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = html_content.encode("utf-8")
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            links = await scraper.fetch_pdf_links()

            assert len(links) > 0
            assert links[0].titulo == "PRAE/RU/UFCA – Cardápio 13/04/2026 a 17/04/2026"
            assert links[0].url == "https://documentos.ufca.edu.br/?post_type=doc&p=45616"

    @pytest.mark.asyncio
    async def test_fetch_pdf_links_no_buttons(self):
        """Deve levantar exceção quando nenhum botão é encontrado."""
        html_content = "<html><body>Nenhum cardápio</body></html>"

        scraper = MenuUrlScraper()

        with patch("src.scraper.menu_url_scraper.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = html_content.encode("utf-8")
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with pytest.raises(MenuUrlNotFoundError):
                await scraper.fetch_pdf_links()

    @pytest.mark.asyncio
    async def test_fetch_pdf_links_connection_error(self):
        """Deve levantar MenuUrlScraperError em erro de conexão."""
        scraper = MenuUrlScraper()

        with patch("src.scraper.menu_url_scraper.requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.ConnectionError("Conexão recusada")

            with pytest.raises(MenuUrlScraperError):
                await scraper.fetch_pdf_links()

    @pytest.mark.asyncio
    async def test_get_latest_pdf(self):
        """Deve retornar o PDF mais recente."""
        html_content = """
        <div class="ui accordion">
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=45616'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-03-16 12:00:37</p>
            </div>
        </div>
        <div class="ui accordion">
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=45614'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-03-15 10:00:00</p>
            </div>
        </div>
        """

        scraper = MenuUrlScraper()

        with patch("src.scraper.menu_url_scraper.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = html_content.encode("utf-8")
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            latest = await scraper.get_latest_pdf()

            # Deve retornar o mais recente (2026-03-16)
            assert "45616" in latest.url

    @pytest.mark.asyncio
    async def test_get_latest_pdf_no_pdfs(self):
        """Deve levantar exceção quando não há PDFs."""
        scraper = MenuUrlScraper()

        with patch("src.scraper.menu_url_scraper.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = "<html><body>Vazio</body></html>".encode("utf-8")
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with pytest.raises(MenuUrlNotFoundError):
                await scraper.get_latest_pdf()
