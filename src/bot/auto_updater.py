"""Atualização automática de cardápios a partir da web."""

import logging
import os
import tempfile
from typing import Optional

from src.cache.menu_cache import MenuCache
from src.scraper.menu_url_scraper import MenuUrlScraper, MenuUrlScraperError
from src.scraper.pdf_downloader import PDFDownloader, PDFDownloadError
from src.scraper.pdf_parser import PDFParser
from src.scraper.table_menu_extractor import TableMenuExtractor
from src.scraper.menu_extractor import MenuExtractor

logger = logging.getLogger(__name__)


class AutoMenuUpdater:
    """
    Orquestra a atualização automática de cardápios.

    Pipeline:
    1. Scrape de URLs do site UFCA
    2. Download do PDF mais recente
    3. Parse do PDF (tabelas ou texto)
    4. Persistência no cache
    """

    def __init__(self, cache: MenuCache):
        """
        Inicializa o atualizador.

        Args:
            cache: Instância do MenuCache para persistência
        """
        self.cache = cache
        self.scraper = MenuUrlScraper()
        self.downloader = PDFDownloader()

    async def update_menu_from_web(self) -> bool:
        """
        Executa o pipeline completo de atualização.

        Retorna:
            True se a atualização foi bem-sucedida, False caso contrário

        Nota:
            Todos os erros são logados. Não levanta exceções (falha silenciosa).
        """
        tmp_path: Optional[str] = None

        try:
            logger.info("=" * 60)
            logger.info("🔄 INICIANDO ATUALIZAÇÃO AUTOMÁTICA DE CARDÁPIOS")
            logger.info("=" * 60)

            # 1. Scrape da página UFCA
            logger.info("Passo 1: Scraping de URLs...")
            try:
                latest_pdf = await self.scraper.get_latest_pdf()
                logger.info(f"PDF encontrado: {latest_pdf.titulo}")
            except MenuUrlScraperError as e:
                logger.error(f"❌ Falha no scraping: {e}")
                return False

            # 2. Download do PDF
            logger.info("Passo 2: Download do PDF...")
            try:
                pdf_bytes = await self.downloader.download(latest_pdf.url)
            except PDFDownloadError as e:
                logger.error(f"❌ Falha no download: {e}")
                return False

            # 3. Parse do PDF
            logger.info("Passo 3: Parse e extração de cardápios...")
            try:
                # Salva em arquivo temporário para parser
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name
                    tmp.write(pdf_bytes)

                # Tenta extrair tabelas (método preferido)
                parser = PDFParser(tmp_path)
                tables = parser.extract_tables()

                if tables:
                    logger.debug("Usando extrator baseado em tabelas")
                    extractor = TableMenuExtractor(tables)
                else:
                    logger.debug("Usando extrator baseado em texto (fallback)")
                    text = parser.extract_text()
                    extractor = MenuExtractor(text)

                weekly_menus = extractor.extract_menus()

                if not weekly_menus:
                    logger.warning("Nenhum cardápio foi extraído do PDF")
                    return False

            except Exception as e:
                logger.error(f"❌ Erro ao fazer parse do PDF: {e}", exc_info=True)
                return False

            # 4. Persistência no cache
            logger.info("Passo 4: Salvando no cache...")
            try:
                for date_str, menu_data in weekly_menus.items():
                    self.cache.save_menu(date_str, menu_data)
                    logger.debug(f"  ✓ {date_str} salvo")

            except Exception as e:
                logger.error(f"❌ Erro ao salvar no cache: {e}", exc_info=True)
                return False

            # Sucesso!
            logger.info("=" * 60)
            logger.info(f"✅ SUCESSO! {len(weekly_menus)} dias de cardápio salvos")
            logger.info("=" * 60)
            return True

        except Exception as e:
            logger.error(f"❌ ERRO INESPERADO: {e}", exc_info=True)
            return False

        finally:
            # Limpa arquivo temporário
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                    logger.debug(f"Arquivo temporário removido: {tmp_path}")
                except OSError as e:
                    logger.warning(f"Erro ao remover arquivo temporário: {e}")
