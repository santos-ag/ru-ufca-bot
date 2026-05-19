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
        """Deve retornar o PDF com a data de cardápio mais recente (não a data de atualização)."""
        html_content = """
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>PRAE/RU/UFCA – Cardápio 11/05/2026 a 15/05/2026</div>
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=45616'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-05-11 12:00:00</p>
            </div>
        </div>
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>PRAE/RU/UFCA – Cardápio 18/05/2026 a 22/05/2026</div>
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=45620'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-04-17 10:00:00</p>
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

            # Deve retornar o cardápio da semana 18-22/05, mesmo com data de atualização mais antiga
            assert "45620" in latest.url
            assert "18/05/2026" in latest.titulo

    @pytest.mark.asyncio
    async def test_sorting_by_title_date_not_cms_date(self):
        """Deve ordenar pela data do cardápio no título, ignorando a data de atualização do CMS.

        Reproduz o bug real: PDF com data de CMS mais antiga pode ter cardápio mais recente.
        """
        html_content = """
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>PRAE/RU/UFCA – Cardápio 11/05/2026 a 15/05/2026</div>
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=46241'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-05-11 14:00:00</p>
            </div>
        </div>
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>PRAE/RU/UFCA – Cardápio 18/05/2026 a 22/05/2026</div>
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=46244'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-04-17 09:00:00</p>
            </div>
        </div>
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>PRAE/RU/UFCA – Cardápio 05/05/2026 a 09/05/2026</div>
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=46239'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-05-05 08:00:00</p>
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

            # Ordem esperada: 18/05 > 11/05 > 05/05 (pela data do cardápio, não do CMS)
            assert len(links) == 3
            assert "46244" in links[0].url  # 18-22/05 (mais recente)
            assert "46241" in links[1].url  # 11-15/05
            assert "46239" in links[2].url  # 05-09/05 (mais antigo)

    @pytest.mark.asyncio
    async def test_sorting_fallback_to_cms_date_when_no_title_date(self):
        """Quando o título não tem data, deve usar data de atualização como fallback."""
        html_content = """
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>Cardápio Semanal</div>
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=1'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-05-11 12:00:00</p>
            </div>
        </div>
        <div class="ui accordion">
            <div class="title"><i class="dropdown icon"></i>Cardápio Semanal</div>
            <div class="content">
                <p><a class="ui teal button" href='https://documentos.ufca.edu.br/?post_type=doc&p=2'></a></p>
                <p style='color: #999; font-size: 0.9em;'>Última atualização: 2026-05-18 12:00:00</p>
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

            # Sem data no título, fallback para data_atualizacao
            assert links[0].url.endswith("p=2")  # 2026-05-18 (mais recente)

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
