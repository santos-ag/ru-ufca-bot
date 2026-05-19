"""
Testes para o TableMenuExtractor.

Seguindo TDD: testes de sanitização e listas limpas devem FALHAR primeiro (RED),
depois implementamos (GREEN).
"""

import re

import pytest
from src.scraper.table_menu_extractor import TableMenuExtractor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_table():
    """
    Tabela mínima simulando estrutura do PDF do RU-UFCA.

    Colunas: col 0 = label, col 1 = 16/mar, col 2 = 17/mar
    """
    return [[
        # linha 0: cabeçalho de datas
        [None,           "16/mar",                     "17/mar"],
        # linha 1: ALMOÇO
        ["ALMOÇO",       "ALMOÇO",                     "ALMOÇO"],
        # linha 2: Principal
        ["Principal",    "FRANGO GRELHADO",             "PEIXE ASSADO"],
        # linha 3: Vegetariano
        ["Vegetariano",  "ROCAMBOLE DE SOJA",           "OMELETE DE FORNO"],
        # linha 4: Saladas — célula com vírgulas internas (causa raiz do bug)
        ["Saladas",      "ALFACE, CENOURA, TOMATE,",   "REPOLHO, BETERRABA,"],
        # linha 5: Guarnição
        ["Guarnição",    "CUSCUZ",                      "MACARRÃO"],
        # linha 6: Acompanhamento — célula com vírgulas internas
        ["Acompanhamentos", "ARROZ BRANCO, FEIJÃO CARIOCA,", "ARROZ INTEGRAL, FEIJÃO PRETO,"],
        # linha 7: Suco
        ["Suco",         "ACEROLA,",                    "CAJU,"],
        # linha 8: Sobremesa
        ["Sobremesa",    "MELANCIA,",                   "MAÇÃ,"],
        # linha 9: JANTAR
        ["JANTAR",       "JANTAR",                      "JANTAR"],
        # linha 10: Principal jantar
        ["Principal",    "CARNE ASSADA",                "FRANGO ACEBOLADO"],
        # linha 11: Saladas jantar — vírgulas
        ["Saladas",      "ALFACE, TOMATE,",             "REPOLHO, CENOURA,"],
        # linha 12: Guarnição jantar
        ["Guarnição",    "FAROFA",                      "CUSCUZ"],
        # linha 13: Acompanhamento jantar
        ["Acompanhamentos", "ARROZ BRANCO, FEIJÃO PRETO,", "ARROZ INTEGRAL, FEIJÃO CARIOCA,"],
        # linha 14: Suco jantar
        ["Suco",         "MANGA,",                      "GOIABA,"],
        # linha 15: Sobremesa jantar
        ["Sobremesa",    "MELÃO,",                      "MAMÃO,"],
    ]]


# ---------------------------------------------------------------------------
# Testes de sanitize_text()
# ---------------------------------------------------------------------------

class TestSanitizeText:
    """Testa a função utilitária sanitize_text."""

    def test_sanitize_removes_trailing_comma(self):
        """Deve remover vírgula no final da string."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("ACEROLA,") == "ACEROLA"

    def test_sanitize_removes_leading_comma(self):
        """Deve remover vírgula no início da string."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text(",ACEROLA") == "ACEROLA"

    def test_sanitize_collapses_double_comma(self):
        """Deve colapsar dupla vírgula em simples."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("ALFACE,, CENOURA") == "ALFACE, CENOURA"

    def test_sanitize_trims_whitespace(self):
        """Deve remover espaços nas bordas."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("  MELANCIA  ") == "MELANCIA"

    def test_sanitize_handles_empty_string(self):
        """Deve retornar string vazia sem erro."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("") == ""

    def test_sanitize_does_not_alter_clean_text(self):
        """Não deve alterar texto já limpo."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("FRANGO GRELHADO") == "FRANGO GRELHADO"

    def test_sanitize_comma_space_comma(self):
        """Deve colapsar ', ,' (vírgula, espaço, vírgula)."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("ALFACE, , CENOURA") == "ALFACE, CENOURA"

    def test_sanitize_replaces_newline_with_space(self):
        """Deve substituir \\n por espaço."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("FRANGO AO MOLHO\nMOSTARDA") == "FRANGO AO MOLHO MOSTARDA"

    def test_sanitize_collapses_multiple_spaces_after_newline(self):
        """Após trocar \\n por espaço, espaços duplos devem ser colapsados."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("FRANGO \n MOSTARDA") == "FRANGO MOSTARDA"

    def test_sanitize_newline_at_end(self):
        """\\n no final deve ser removido."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("MAÇÃ\nDOCE\n") == "MAÇÃ DOCE"

    def test_sanitize_escapes_asterisk(self):
        """Deve escapar asteriscos para não quebrar Markdown do Telegram."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("PEIXE FRITO*") == "PEIXE FRITO\\*"

    def test_sanitize_escapes_multiple_asterisks(self):
        """Deve escapar múltiplos asteriscos."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("FRANGO* COM MOLHO*") == "FRANGO\\* COM MOLHO\\*"

    def test_sanitize_asterisk_in_middle(self):
        """Deve escapar asterisco no meio do texto."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("CENOURA AO MOLHO BRANCO*") == "CENOURA AO MOLHO BRANCO\\*"

    def test_sanitize_escapes_underscore(self):
        """Deve escapar underscores para não quebrar Markdown do Telegram."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("ARROZ_INTEGRAL") == "ARROZ\\_INTEGRAL"

    def test_sanitize_escapes_multiple_underscores(self):
        """Deve escapar múltiplos underscores."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("ARROZ_INTEGRAL_TEMPERADO") == "ARROZ\\_INTEGRAL\\_TEMPERADO"

    def test_sanitize_replaces_crlf_with_space(self):
        """Deve substituir \\r\\n (Windows) por espaço."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("FRANGO AO MOLHO\r\nMOSTARDA") == "FRANGO AO MOLHO MOSTARDA"

    def test_sanitize_replaces_cr_with_space(self):
        """Deve substituir \\r (Mac antigo) por espaço."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("FRANGO AO MOLHO\rMOSTARDA") == "FRANGO AO MOLHO MOSTARDA"

    def test_sanitize_handles_mixed_line_endings(self):
        """Deve lidar com múltiplos tipos de quebra de linha."""
        from src.scraper.table_menu_extractor import sanitize_text

        assert sanitize_text("A\nB\r\nC\rD") == "A B C D"


# ---------------------------------------------------------------------------
# Testes de \\n em campos extraídos do PDF
# ---------------------------------------------------------------------------

@pytest.fixture
def table_with_newlines():
    """
    Tabela com células contendo \\n internos, replicando o que o pdfplumber
    retorna para células com múltiplas linhas de texto no PDF.
    """
    return [[
        [None,        "16/mar",                        "17/mar"],
        ["ALMOÇO",    "ALMOÇO",                        "ALMOÇO"],
        ["Principal", "FRANGO AO MOLHO\nMOSTARDA",     "PEIXE ASSADO"],
        ["Vegetariano","LASANHA A BOLHONESA DE\nSOJA", "OMELETE"],
        ["Saladas",   "TOMATE E\nMANGA",               "REPOLHO"],
        ["Guarnição", "CUSCUZ",                        "FAROFA"],
        ["Acompanhamentos", "ARROZ BRANCO\nARROZ INTEGRAL\nFEIJÃO CARIOCA", "ARROZ INTEGRAL"],
        ["Suco",      "ACEROLA",                       "CAJU"],
        ["Sobremesa", "MAÇÃ\nDOCE",                    "MELANCIA"],
        ["JANTAR",    "JANTAR",                        "JANTAR"],
        ["Principal", "CARNE ASSADA",                  "FRANGO ACEBOLADO"],
        ["Suco",      "MANGA",                         "GOIABA"],
        ["Sobremesa", "MELÃO\nDOCE",                   "MAMÃO"],
    ]]


class TestNewlineInFields:
    """Garante que \\n internos não aparecem em nenhum campo extraído."""

    def test_prato_principal_has_no_newline(self, table_with_newlines):
        """prato_principal não deve conter \\n."""
        extractor = TableMenuExtractor(table_with_newlines)
        menus = extractor.extract_menus()

        valor = menus["2026-03-16"]["almoco"]["prato_principal"]
        assert "\n" not in valor, f"\\n encontrado em prato_principal: {valor!r}"

    def test_vegetariano_has_no_newline(self, table_with_newlines):
        """vegetariano não deve conter \\n."""
        extractor = TableMenuExtractor(table_with_newlines)
        menus = extractor.extract_menus()

        valor = menus["2026-03-16"]["almoco"]["vegetariano"]
        assert "\n" not in valor, f"\\n encontrado em vegetariano: {valor!r}"

    def test_saladas_items_have_no_newline(self, table_with_newlines):
        """Nenhum item de saladas deve conter \\n."""
        extractor = TableMenuExtractor(table_with_newlines)
        menus = extractor.extract_menus()

        for item in menus["2026-03-16"]["almoco"]["saladas"]:
            assert "\n" not in item, f"\\n encontrado em saladas: {item!r}"

    def test_acompanhamentos_items_have_no_newline(self, table_with_newlines):
        """Nenhum item de acompanhamentos deve conter \\n."""
        extractor = TableMenuExtractor(table_with_newlines)
        menus = extractor.extract_menus()

        for item in menus["2026-03-16"]["almoco"]["acompanhamentos"]:
            assert "\n" not in item, f"\\n encontrado em acompanhamentos: {item!r}"

    def test_sobremesa_has_no_newline(self, table_with_newlines):
        """sobremesa não deve conter \\n."""
        extractor = TableMenuExtractor(table_with_newlines)
        menus = extractor.extract_menus()

        valor = menus["2026-03-16"]["almoco"]["sobremesa"]
        assert "\n" not in valor, f"\\n encontrado em sobremesa: {valor!r}"

    def test_formatted_output_has_no_newline_artifacts(self, table_with_newlines):
        """Mensagem formatada final não deve ter \\n dentro de campos de conteúdo."""
        from src.bot.formatter import MenuFormatter

        extractor = TableMenuExtractor(table_with_newlines)
        menus = extractor.extract_menus()

        formatter = MenuFormatter()
        output = formatter.format_full_menu(menus["2026-03-16"], "2026-03-16")

        # Cada linha do output deve ser uma linha inteira — sem \n embutido em valores
        for line in output.split("\n"):
            assert "\n" not in line, f"\\n embutido encontrado: {line!r}"


# ---------------------------------------------------------------------------
# Testes de listas sem vírgulas residuais
# ---------------------------------------------------------------------------

class TestListFieldsNoDanglingCommas:
    """
    Verifica que saladas e acompanhamentos não contêm vírgulas residuais
    nos itens individuais da lista.
    """

    def test_saladas_items_have_no_trailing_comma(self, simple_table):
        """Cada item de saladas não deve terminar com vírgula."""
        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        almoco = menus["2026-03-16"]["almoco"]
        for item in almoco["saladas"]:
            assert not item.endswith(","), f"Item com vírgula residual: {item!r}"

    def test_acompanhamentos_items_have_no_trailing_comma(self, simple_table):
        """Cada item de acompanhamentos não deve terminar com vírgula."""
        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        almoco = menus["2026-03-16"]["almoco"]
        for item in almoco["acompanhamentos"]:
            assert not item.endswith(","), f"Item com vírgula residual: {item!r}"

    def test_suco_has_no_trailing_comma(self, simple_table):
        """Campo suco não deve conter vírgula."""
        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        almoco = menus["2026-03-16"]["almoco"]
        assert "," not in almoco["suco"], f"Suco com vírgula: {almoco['suco']!r}"

    def test_sobremesa_has_no_trailing_comma(self, simple_table):
        """Campo sobremesa não deve conter vírgula."""
        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        almoco = menus["2026-03-16"]["almoco"]
        assert "," not in almoco["sobremesa"], \
            f"Sobremesa com vírgula: {almoco['sobremesa']!r}"

    def test_jantar_saladas_items_have_no_trailing_comma(self, simple_table):
        """Saladas do jantar também não devem ter vírgulas residuais."""
        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        janta = menus["2026-03-16"]["janta"]
        for item in janta["saladas"]:
            assert not item.endswith(","), f"Item com vírgula residual: {item!r}"


# ---------------------------------------------------------------------------
# Testes de conteúdo esperado (split por vírgula, não por espaço)
# ---------------------------------------------------------------------------

class TestListSplitByComma:
    """
    Verifica que listas são construídas dividindo por vírgula (não espaço),
    preservando itens compostos como 'ARROZ BRANCO' como um único item.
    """

    def test_saladas_split_preserves_multi_word_items(self, simple_table):
        """
        'ALFACE, CENOURA, TOMATE' deve virar ['ALFACE', 'CENOURA', 'TOMATE'],
        não ['ALFACE,', 'CENOURA,', 'TOMATE'].
        """
        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        almoco = menus["2026-03-16"]["almoco"]
        # Deve ter pelo menos 2 itens distintos
        assert len(almoco["saladas"]) >= 2

    def test_acompanhamentos_preserves_multi_word_items(self, simple_table):
        """
        'ARROZ BRANCO, FEIJÃO CARIOCA' deve virar
        ['ARROZ BRANCO', 'FEIJÃO CARIOCA'], não ['ARROZ', 'BRANCO,', ...].
        """
        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        almoco = menus["2026-03-16"]["almoco"]
        assert "Arroz Branco" in almoco["acompanhamentos"] or \
               any("ARROZ" in item for item in almoco["acompanhamentos"])


# ---------------------------------------------------------------------------
# Testes de formatação final (integração com formatter)
# ---------------------------------------------------------------------------

class TestFormatterIntegration:
    """
    Garante que o texto final formatado não contém dupla vírgula.
    """

    def test_formatted_output_has_no_double_comma(self, simple_table):
        """A mensagem formatada final não deve conter ',,' ou ', ,'."""
        from src.bot.formatter import MenuFormatter

        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        formatter = MenuFormatter()
        output = formatter.format_full_menu(menus["2026-03-16"], "2026-03-16")

        assert ",," not in output, f"Dupla vírgula encontrada:\n{output}"
        assert ", ," not in output, f"', ,' encontrada:\n{output}"

    def test_formatted_suco_no_trailing_comma(self, simple_table):
        """Suco formatado não deve ter vírgula residual."""
        from src.bot.formatter import MenuFormatter

        extractor = TableMenuExtractor(simple_table)
        menus = extractor.extract_menus()

        formatter = MenuFormatter()
        output = formatter.format_meal(menus["2026-03-16"]["almoco"], "Almoço")

        # A linha de suco não deve terminar com vírgula
        for line in output.splitlines():
            if "Suco" in line:
                assert not line.rstrip().endswith(","), \
                    f"Linha de suco com vírgula: {line!r}"


# ---------------------------------------------------------------------------
# Fixture e testes do bug: data solta capturada na Sobremesa
# ---------------------------------------------------------------------------

@pytest.fixture
def table_with_jantar_date_row():
    """
    Tabela que reproduz o bug real: linha de datas do JANTAR aparece entre
    a Sobremesa do ALMOÇO e a linha 'JANTAR', fazendo a data vazar para
    o campo sobremesa (ex: 'DOCE 20/mar').

    Estrutura fiel ao PDF do RU-UFCA:
      ...linhas do ALMOÇO...
      Sobremesa   | MELANCIA  | MAÇÃ
      [linha de datas do JANTAR: None | 16/mar | 17/mar]  ← bug aqui
      JANTAR      | JANTAR    | JANTAR
      ...linhas do JANTAR...
    """
    return [[
        # linha 0: cabeçalho de datas do ALMOÇO
        [None,        "16/mar",          "17/mar"],
        # linha 1: ALMOÇO
        ["ALMOÇO",    "ALMOÇO",          "ALMOÇO"],
        # linha 2: Principal
        ["Principal", "FRANGO GRELHADO", "PEIXE ASSADO"],
        # linha 3: Suco
        ["Suco",      "ACEROLA",         "CAJU"],
        # linha 4: Sobremesa do ALMOÇO
        ["Sobremesa", "MELANCIA",        "MAÇÃ"],
        # linha 5: linha de datas do JANTAR (causa do bug — célula col 1 = "16/mar")
        [None,        "16/mar",          "17/mar"],
        # linha 6: JANTAR
        ["JANTAR",    "JANTAR",          "JANTAR"],
        # linha 7: Principal jantar
        ["Principal", "CARNE ASSADA",    "FRANGO ACEBOLADO"],
        # linha 8: Suco jantar
        ["Suco",      "MANGA",           "GOIABA"],
        # linha 9: Sobremesa jantar
        ["Sobremesa", "MELÃO",           "MAMÃO"],
    ]]


class TestDateLeakBug:
    """
    Garante que cabeçalhos de data (ex: '16/mar', '20/mar') não vazam
    para campos de conteúdo como sobremesa e suco.
    """

    def test_sobremesa_almoco_has_no_date_string(self, table_with_jantar_date_row):
        """
        Sobremesa do almoço não deve conter padrão de data (ex: '16/mar').

        Reproduz o bug: 'MELANCIA' não deve virar 'MELANCIA 16/mar'.
        """
        extractor = TableMenuExtractor(table_with_jantar_date_row)
        menus = extractor.extract_menus()

        sobremesa = menus["2026-03-16"]["almoco"]["sobremesa"]
        assert not re.search(r'\d{1,2}/[a-z]{3}', sobremesa, re.I), \
            f"Data vazou para sobremesa do almoço: {sobremesa!r}"

    def test_suco_almoco_has_no_date_string(self, table_with_jantar_date_row):
        """Suco do almoço não deve conter padrão de data."""
        extractor = TableMenuExtractor(table_with_jantar_date_row)
        menus = extractor.extract_menus()

        suco = menus["2026-03-16"]["almoco"]["suco"]
        assert not re.search(r'\d{1,2}/[a-z]{3}', suco, re.I), \
            f"Data vazou para suco do almoço: {suco!r}"

    def test_sobremesa_almoco_value_is_correct(self, table_with_jantar_date_row):
        """Sobremesa do almoço deve ser 'MELANCIA', não 'MELANCIA 16/mar'."""
        extractor = TableMenuExtractor(table_with_jantar_date_row)
        menus = extractor.extract_menus()

        sobremesa = menus["2026-03-16"]["almoco"]["sobremesa"]
        assert sobremesa == "Melancia", \
            f"Valor incorreto para sobremesa: {sobremesa!r}"

    def test_sobremesa_jantar_has_no_date_string(self, table_with_jantar_date_row):
        """Sobremesa do jantar também não deve conter padrão de data."""
        extractor = TableMenuExtractor(table_with_jantar_date_row)
        menus = extractor.extract_menus()

        sobremesa = menus["2026-03-16"]["janta"]["sobremesa"]
        assert not re.search(r'\d{1,2}/[a-z]{3}', sobremesa, re.I), \
            f"Data vazou para sobremesa do jantar: {sobremesa!r}"

    def test_formatted_output_has_no_date_in_sobremesa(self, table_with_jantar_date_row):
        """A mensagem formatada final não deve conter data no campo Sobremesa."""
        from src.bot.formatter import MenuFormatter

        extractor = TableMenuExtractor(table_with_jantar_date_row)
        menus = extractor.extract_menus()

        formatter = MenuFormatter()
        output = formatter.format_full_menu(menus["2026-03-16"], "2026-03-16")

        for line in output.splitlines():
            if "Sobremesa" in line:
                assert not re.search(r'\d{1,2}/[a-z]{3}', line, re.I), \
                    f"Data encontrada na linha de Sobremesa: {line!r}"
