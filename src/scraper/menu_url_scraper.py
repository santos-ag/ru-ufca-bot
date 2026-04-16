"""Scraper de URLs dos PDFs de cardápio do site oficial UFCA."""

import logging
from typing import List, Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MenuUrlNotFoundError(Exception):
    """Exceção levantada quando nenhuma URL de cardápio é encontrada."""
    pass


class MenuUrlScraperError(Exception):
    """Exceção geral do scraper."""
    pass


class MenuPdfLink:
    """Value Object que representa um link de PDF de cardápio."""

    def __init__(self, titulo: str, url: str, data_atualizacao: str):
        """
        Args:
            titulo: Título do cardápio (ex: "PRAE/RU/UFCA – Cardápio 13/04/2026 a 17/04/2026")
            url: URL completa do PDF
            data_atualizacao: Data de última atualização (ex: "2026-03-16 12:00:37")
        """
        self.titulo = titulo
        self.url = url
        self.data_atualizacao = data_atualizacao

    def __repr__(self) -> str:
        return f"MenuPdfLink(titulo='{self.titulo}', url='{self.url}')"


class MenuUrlScraper:
    """
    Scraper de URLs dos PDFs do site oficial do RU UFCA.

    Extrai links dos botões 'Baixar documento' da página:
    https://www.ufca.edu.br/assuntos-estudantis/refeitorio-universitario/cardapios/
    """

    DEFAULT_URL = "https://www.ufca.edu.br/assuntos-estudantis/refeitorio-universitario/cardapios/"
    TIMEOUT = 30
    BUTTON_CLASS = "ui teal button"

    def __init__(self, url: str = DEFAULT_URL):
        """
        Inicializa o scraper.

        Args:
            url: URL da página de cardápios (pode ser sobrescrita para testes)
        """
        self.url = url

    async def fetch_pdf_links(self) -> List[MenuPdfLink]:
        """
        Scrape da página e extração de URLs dos PDFs.

        Retorna:
            Lista de MenuPdfLink ordenada por data de atualização (mais recente primeiro)

        Levanta:
            MenuUrlScraperError: Se houver erro de conexão ou parsing
        """
        try:
            logger.info(f"Iniciando scrape de cardápios em {self.url}")

            response = requests.get(self.url, timeout=self.TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Busca todos os botões com classe "ui teal button"
            buttons = soup.find_all("a", class_=self.BUTTON_CLASS)

            if not buttons:
                logger.warning("Nenhum botão 'ui teal button' encontrado na página")
                raise MenuUrlNotFoundError("Nenhum PDF de cardápio encontrado na página")

            pdf_links: List[MenuPdfLink] = []

            # Itera sobre cada botão encontrado
            for button in buttons:
                try:
                    pdf_url = button.get("href")
                    if not pdf_url:
                        continue

                    # Busca o título no elemento pai (accordion title)
                    titulo_elem = button.find_parent("div", class_="content")
                    if titulo_elem:
                        titulo_parent = titulo_elem.find_parent("div", class_="ui accordion")
                        if titulo_parent:
                            title_elem = titulo_parent.find("div", class_="title")
                            titulo = title_elem.get_text(strip=True) if title_elem else "Cardápio"
                        else:
                            titulo = "Cardápio"
                    else:
                        titulo = "Cardápio"

                    # Busca a data de última atualização
                    data_elem = button.find_parent("div", class_="content")
                    data_atualizacao = ""
                    if data_elem:
                        time_elem = data_elem.find("p", style=lambda x: x and "color: #999" in x)
                        if time_elem:
                            text = time_elem.get_text(strip=True)
                            # Extrai apenas a data (ex: "2026-03-16 12:00:37")
                            if "Última atualização:" in text:
                                data_atualizacao = text.split("Última atualização:")[-1].strip()

                    pdf_link = MenuPdfLink(titulo, pdf_url, data_atualizacao)
                    pdf_links.append(pdf_link)
                    logger.debug(f"PDF encontrado: {pdf_link}")

                except Exception as e:
                    logger.warning(f"Erro ao processar botão: {e}")
                    continue

            if not pdf_links:
                raise MenuUrlNotFoundError("Nenhum PDF válido foi extraído")

            # Ordena por data de atualização (mais recente primeiro)
            pdf_links.sort(
                key=lambda x: x.data_atualizacao if x.data_atualizacao else "",
                reverse=True
            )

            logger.info(f"✅ {len(pdf_links)} PDF(s) encontrado(s)")
            return pdf_links

        except requests.RequestException as e:
            error_msg = f"Erro ao conectar ao site UFCA: {e}"
            logger.error(error_msg)
            raise MenuUrlScraperError(error_msg) from e

        except MenuUrlNotFoundError:
            raise

        except Exception as e:
            error_msg = f"Erro inesperado durante scrape: {e}"
            logger.error(error_msg, exc_info=True)
            raise MenuUrlScraperError(error_msg) from e

    async def get_latest_pdf(self) -> MenuPdfLink:
        """
        Retorna apenas o PDF mais recente.

        Retorna:
            MenuPdfLink do cardápio mais recente

        Levanta:
            MenuUrlScraperError: Se nenhum PDF for encontrado ou houver erro
        """
        links = await self.fetch_pdf_links()
        if not links:
            raise MenuUrlScraperError("Nenhum PDF disponível")
        return links[0]
