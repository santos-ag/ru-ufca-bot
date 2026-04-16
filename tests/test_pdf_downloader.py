"""Testes para PDFDownloader - Download de PDFs."""

import pytest
from unittest.mock import Mock, patch

from src.scraper.pdf_downloader import PDFDownloader, PDFDownloadError


class TestPDFDownloader:
    """Testes do PDFDownloader."""

    def test_downloader_initialization_defaults(self):
        """Deve inicializar com valores padrão."""
        downloader = PDFDownloader()
        assert downloader.timeout == PDFDownloader.TIMEOUT
        assert downloader.max_size_bytes == PDFDownloader.MAX_SIZE_MB * 1024 * 1024

    def test_downloader_initialization_custom(self):
        """Deve inicializar com valores customizados."""
        downloader = PDFDownloader(timeout=60, max_size_mb=100)
        assert downloader.timeout == 60
        assert downloader.max_size_bytes == 100 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_download_success(self):
        """Deve fazer download com sucesso."""
        pdf_content = b"%PDF-1.4\n" + b"x" * 1000  # Simula PDF mínimo

        downloader = PDFDownloader()

        with patch("src.scraper.pdf_downloader.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {"content-type": "application/pdf"}
            mock_response.iter_content = Mock(return_value=[pdf_content])
            mock_get.return_value = mock_response

            result = await downloader.download("https://example.com/test.pdf")

            assert result == pdf_content
            assert len(result) == len(pdf_content)

    @pytest.mark.asyncio
    async def test_download_wrong_content_type(self):
        """Deve rejeitar conteúdo não-PDF."""
        downloader = PDFDownloader()

        with patch("src.scraper.pdf_downloader.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {"content-type": "text/html"}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with pytest.raises(PDFDownloadError) as exc_info:
                await downloader.download("https://example.com/test.html")

            assert "Tipo de conteúdo inesperado" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_exceeds_size_limit(self):
        """Deve rejeitar PDF muito grande."""
        downloader = PDFDownloader(max_size_mb=1)

        with patch("src.scraper.pdf_downloader.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {"content-type": "application/pdf"}
            # Simula 2MB (excede limite de 1MB)
            large_chunk = b"x" * (2 * 1024 * 1024)
            mock_response.iter_content = Mock(return_value=[large_chunk])
            mock_get.return_value = mock_response

            with pytest.raises(PDFDownloadError) as exc_info:
                await downloader.download("https://example.com/large.pdf")

            assert "excede tamanho máximo" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_connection_error(self):
        """Deve levantar exceção em erro de conexão."""
        downloader = PDFDownloader()

        with patch("src.scraper.pdf_downloader.requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.ConnectionError("Conexão recusada")

            with pytest.raises(PDFDownloadError) as exc_info:
                await downloader.download("https://example.com/test.pdf")

            assert "Erro ao baixar PDF" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_multiple_chunks(self):
        """Deve concatenar múltiplos chunks corretamente."""
        chunk1 = b"%PDF-1.4\n"
        chunk2 = b"..." + b"x" * 100
        chunk3 = b"y" * 50

        downloader = PDFDownloader()

        with patch("src.scraper.pdf_downloader.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {"content-type": "application/pdf"}
            mock_response.iter_content = Mock(return_value=[chunk1, chunk2, chunk3])
            mock_get.return_value = mock_response

            result = await downloader.download("https://example.com/test.pdf")

            assert result == chunk1 + chunk2 + chunk3

    @pytest.mark.asyncio
    async def test_download_timeout(self):
        """Deve respeitar timeout configurado."""
        downloader = PDFDownloader(timeout=5)

        with patch("src.scraper.pdf_downloader.requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.Timeout("Timeout")

            with pytest.raises(PDFDownloadError) as exc_info:
                await downloader.download("https://example.com/test.pdf")

            assert "Erro ao baixar PDF" in str(exc_info.value)
