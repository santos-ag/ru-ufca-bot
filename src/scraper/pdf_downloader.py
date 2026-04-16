"""Download de PDFs de cardápio de URLs externas."""

import logging
from typing import Optional
from io import BytesIO

import requests

logger = logging.getLogger(__name__)


class PDFDownloadError(Exception):
    """Exceção levantada quando o download falha."""
    pass


class PDFDownloader:
    """
    Realiza download de arquivos PDF de URLs externas.

    Responsável por:
    - Fazer requisições HTTP seguras
    - Validar o tipo de conteúdo
    - Retornar bytes do PDF ou levantar exceção
    """

    TIMEOUT = 30
    MAX_SIZE_MB = 50  # Limite de tamanho para PDFs

    def __init__(self, timeout: int = TIMEOUT, max_size_mb: int = MAX_SIZE_MB):
        """
        Inicializa o downloader.

        Args:
            timeout: Timeout em segundos para requisições HTTP
            max_size_mb: Tamanho máximo do PDF em MB
        """
        self.timeout = timeout
        self.max_size_bytes = max_size_mb * 1024 * 1024

    async def download(self, url: str) -> bytes:
        """
        Realiza download de um PDF.

        Args:
            url: URL completa do PDF

        Retorna:
            bytes do PDF

        Levanta:
            PDFDownloadError: Se houver erro no download
        """
        try:
            logger.info(f"Iniciando download do PDF: {url}")

            # Realiza a requisição
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Valida tipo de conteúdo
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type:
                error_msg = f"Tipo de conteúdo inesperado: {content_type}"
                logger.error(error_msg)
                raise PDFDownloadError(error_msg)

            # Lê o conteúdo com validação de tamanho
            content = BytesIO()
            downloaded_size = 0

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > self.max_size_bytes:
                        max_size_mb = self.max_size_bytes // (1024 * 1024)
                        error_msg = f"PDF excede tamanho máximo ({max_size_mb}MB)"
                        logger.error(error_msg)
                        raise PDFDownloadError(error_msg)
                    content.write(chunk)

            pdf_bytes = content.getvalue()
            logger.info(f"✅ PDF baixado com sucesso: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except requests.RequestException as e:
            error_msg = f"Erro ao baixar PDF: {e}"
            logger.error(error_msg)
            raise PDFDownloadError(error_msg) from e

        except PDFDownloadError:
            raise

        except Exception as e:
            error_msg = f"Erro inesperado durante download: {e}"
            logger.error(error_msg, exc_info=True)
            raise PDFDownloadError(error_msg) from e
