"""
Módulo de scraping e parsing.

Responsável por extrair e processar dados dos PDFs de cardápios.
"""

from .pdf_parser import PDFParser
from .menu_extractor import MenuExtractor
from .table_menu_extractor import TableMenuExtractor
from .llm_cleaner import clean_meal_data_with_llm

__all__ = ["PDFParser", "MenuExtractor", "TableMenuExtractor", "clean_meal_data_with_llm"]
