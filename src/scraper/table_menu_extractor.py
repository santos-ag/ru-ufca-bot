"""Extrai cardápios usando estrutura de tabela do PDF."""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


def sanitize_text(text: str) -> str:
    """
    Limpa e normaliza texto extraído de PDF para exibição no Telegram.

    Operações (em ordem):
        1. Normaliza quebras de linha (\\n, \\r\\n, \\r) para espaço
        2. Colapsa espaços múltiplos em um único espaço
        3. Colapsa sequências de vírgulas (com ou sem espaços) em uma só
        4. Remove espaços e vírgulas no início e no final
        5. Escapa caracteres especiais do Markdown (* e _)

    Args:
        text: Texto bruto extraído do PDF.

    Returns:
        Texto sanitizado e pronto para envio ao Telegram.
    """
    if not text:
        return ""
    # 1. Normalizar todas as variantes de quebra de linha para espaço
    text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    # 2. Colapsar espaços múltiplos em um único espaço
    text = re.sub(r' {2,}', ' ', text)
    # 3. Colapsar vírgulas duplicadas/triplas com espaços opcionais entre elas
    text = re.sub(r',(\s*,)+', ',', text)
    # 4. Remover espaços e vírgulas nas bordas
    text = re.sub(r'^[\s,]+|[\s,]+$', '', text)
    # 5. Escapar caracteres especiais do Markdown do Telegram
    text = text.replace('*', '\\*').replace('_', '\\_')
    return text


class TableMenuExtractor:
    """Extrai cardápios de tabelas do PDF preservando colunas."""
    
    def __init__(self, tables: List[List[List[Optional[str]]]]):
        """
        Inicializa com as tabelas extraídas do PDF.
        
        Args:
            tables: Lista de tabelas onde cada tabela é uma lista de linhas (listas de células)
        """
        self.tables = tables
    
    def extract_menus(self) -> Dict[str, Dict[str, Any]]:
        """
        Extrai cardápios organizados por data ISO.
        
        Formato: {"2026-03-16": {"almoco": {...}, "janta": {...}}}
        """
        if not self.tables:
            return {}
        
        menus = {}
        
        for table in self.tables:
            # Detectar ano
            year = 2026
            for row in table[:5]:
                for cell in row:
                    if cell:
                        year_match = re.search(r'\b(20\d{2})\b', cell)
                        if year_match:
                            year = int(year_match.group(1))
                            break
            
            # Procurar linhas com "ALMOÇO" e "JANTAR"
            almoco_row_idx = None
            jantar_row_idx = None
            date_columns = {}  # {col_idx: date_str}
            
            for i, row in enumerate(table):
                first_cell = row[0] if row else None
                
                if first_cell:
                    if 'ALMOÇO' in first_cell.upper():
                        almoco_row_idx = i
                        # Procurar linha de datas antes do almoço
                        for j in range(max(0, i - 2), i + 1):
                            if j < len(table):
                                for col_idx, cell in enumerate(table[j]):
                                    if cell:
                                        match = re.search(r'(\d{1,2}/[a-z]{3})', cell, re.I)
                                        if match and col_idx > 0:  # Skip column 0 (labels)
                                            date_columns[col_idx] = match.group(1)
                    
                    elif 'JANTAR' in first_cell.upper():
                        jantar_row_idx = i
            
            if not date_columns:
                continue
            
            # Extrair almoços para cada data
            if almoco_row_idx is not None:
                # Encontrar fim da seção de almoço (antes do jantar ou no máximo +15 linhas)
                almoco_end = jantar_row_idx if jantar_row_idx else min(almoco_row_idx + 15, len(table))
                
                for col_idx, date_str in date_columns.items():
                    iso_date = self.normalize_date(date_str, year)
                    if iso_date not in menus:
                        menus[iso_date] = {}
                    
                    menus[iso_date]['almoco'] = self._extract_meal_from_table(
                        table, almoco_row_idx, almoco_end, col_idx
                    )
            
            # Extrair jantares para cada data
            if jantar_row_idx is not None:
                jantar_end = min(jantar_row_idx + 15, len(table))
                
                for col_idx, date_str in date_columns.items():
                    iso_date = self.normalize_date(date_str, year)
                    if iso_date not in menus:
                        menus[iso_date] = {}
                    
                    menus[iso_date]['janta'] = self._extract_meal_from_table(
                        table, jantar_row_idx, jantar_end, col_idx
                    )
        
        return menus
    
    def _extract_meal_from_table(
        self, 
        table: List[List[Optional[str]]], 
        meal_row_idx: int,
        meal_end_idx: int,
        col_idx: int
    ) -> Dict[str, Any]:
        """
        Extrai dados de uma refeição de uma coluna específica da tabela.
        
        Args:
            table: Tabela completa
            meal_row_idx: Índice da linha que contém "ALMOÇO" ou "JANTAR"
            meal_end_idx: Índice da linha onde termina a seção da refeição
            col_idx: Índice da coluna da data
        
        Returns:
            Dicionário com categorias do cardápio
        """
        meal_data = {
            "prato_principal": "",
            "vegetariano": "",
            "acompanhamentos": [],
            "saladas": [],
            "suco": "",
            "sobremesa": ""
        }
        
        # Mapear labels de categoria para suas linhas
        category_rows = {}
        
        for i in range(meal_row_idx, min(meal_end_idx, len(table))):
            if i >= len(table):
                break
            
            row = table[i]
            first_cell = row[0] if row and len(row) > 0 else None
            
            if not first_cell:
                continue
            
            label = first_cell.strip()
            
            if 'Principal' in label:
                category_rows['Principal'] = i
            elif 'Vegetariano' in label:
                category_rows['Vegetariano'] = i
            elif 'Saladas' in label:
                category_rows['Saladas'] = i
            elif 'Guarnição' in label:
                category_rows['Guarnição'] = i
            elif 'Acompanhamento' in label:
                category_rows['Acompanhamento'] = i
            elif 'Suco' in label:
                category_rows['Suco'] = i
            elif 'Sobremesa' in label:
                category_rows['Sobremesa'] = i
        
        # Função helper para extrair texto de uma categoria (pode ter múltiplas linhas)
        def get_category_text(category: str) -> str:
            """Extrai texto completo de uma categoria juntando múltiplas linhas."""
            if category not in category_rows:
                return ""
            
            start_row = category_rows[category]
            
            # Encontrar próxima categoria para definir fim
            category_order = ['Principal', 'Vegetariano', 'Saladas', 'Guarnição', 
                             'Acompanhamento', 'Suco', 'Sobremesa']
            
            try:
                current_idx = category_order.index(category)
            except ValueError:
                current_idx = -1
            
            end_row = meal_end_idx
            for next_cat in category_order[current_idx + 1:]:
                if next_cat in category_rows:
                    end_row = category_rows[next_cat]
                    break
            
            # Juntar texto de todas as linhas da categoria
            parts = []
            for row_idx in range(start_row, min(end_row, len(table))):
                if row_idx >= len(table):
                    break

                row = table[row_idx]
                if col_idx < len(row):
                    cell = row[col_idx]
                    if cell and cell.strip():
                        # Ignorar células que são cabeçalhos de data (ex: "16/mar", "20/mar")
                        if re.match(r'^\d{1,2}/[a-z]{3}$', cell.strip(), re.I):
                            continue
                        parts.append(cell.strip())
            
            return ' '.join(parts)
        
        # Extrair cada categoria
        raw_data = {
            "principal": get_category_text('Principal'),
            "vegetariano": get_category_text('Vegetariano'),
            "saladas": get_category_text('Saladas'),
            "guarnição": get_category_text('Guarnição'),
            "acompanhamento": get_category_text('Acompanhamento'),
            "suco": get_category_text('Suco'),
            "sobremesa": get_category_text('Sobremesa')
        }
        
        from src.scraper.llm_cleaner import clean_meal_data_with_llm
        meal_data = clean_meal_data_with_llm(raw_data)
        
        return meal_data
    
    def normalize_date(self, date_str: str, year: int) -> str:
        """Converte "16/mar" para "2026-03-16"."""
        months_pt = {
            'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4,
            'mai': 5, 'jun': 6, 'jul': 7, 'ago': 8,
            'set': 9, 'out': 10, 'nov': 11, 'dez': 12
        }
        
        match = re.match(r'(\d{1,2})/([a-z]{3})', date_str, re.IGNORECASE)
        if not match:
            return f"{year}-01-01"
        
        day = int(match.group(1))
        month = months_pt.get(match.group(2).lower(), 1)
        
        try:
            return datetime(year, month, day).strftime('%Y-%m-%d')
        except ValueError:
            return f"{year}-01-01"
