"""
Testes para o formatador de mensagens.

Seguindo TDD: Estes testes devem FALHAR primeiro (RED), depois implementamos (GREEN).
"""

import pytest
from datetime import date


class TestMenuFormatter:
    """
    Testes para a classe MenuFormatter.
    
    Responsabilidades:
    - Formatar cardápios em mensagens para Telegram
    - Adicionar emojis apropriados
    - Formatar datas em português
    """
    
    @pytest.fixture
    def sample_menu(self):
        """Cardápio de exemplo para testes."""
        return {
            "prato_principal": "Frango Grelhado",
            "vegetariano": "Lasanha de Soja",
            "acompanhamentos": ["Arroz Branco", "Feijão Carioca", "Farofa"],
            "saladas": ["Alface", "Tomate"],
            "suco": "Acerola",
            "sobremesa": "Melancia"
        }
    
    def test_format_meal_returns_string(self, sample_menu):
        """
        Teste: Deve retornar uma string formatada.
        
        Arrange: Cardápio válido
        Act: Formatar cardápio
        Assert: Retorna string não-vazia
        """
        from src.bot.formatter import MenuFormatter
        
        formatter = MenuFormatter()
        message = formatter.format_meal(sample_menu, "Almoço")
        
        assert isinstance(message, str)
        assert len(message) > 0
    
    def test_format_meal_contains_meal_type(self, sample_menu):
        """
        Teste: Mensagem deve conter o tipo de refeição.
        
        Arrange: Cardápio e tipo "Almoço"
        Act: Formatar
        Assert: Contém "Almoço" ou "ALMOÇO"
        """
        from src.bot.formatter import MenuFormatter
        
        formatter = MenuFormatter()
        message = formatter.format_meal(sample_menu, "Almoço")
        
        assert "Almoço" in message or "ALMOÇO" in message
    
    def test_format_meal_contains_dish_items(self, sample_menu):
        """
        Teste: Mensagem deve conter itens do cardápio.
        
        Arrange: Cardápio com pratos específicos
        Act: Formatar
        Assert: Contém "Frango Grelhado" e outros itens
        """
        from src.bot.formatter import MenuFormatter
        
        formatter = MenuFormatter()
        message = formatter.format_meal(sample_menu, "Almoço")
        
        assert "Frango Grelhado" in message
        assert "Arroz Branco" in message
        assert "Acerola" in message
    
    def test_format_meal_contains_emojis(self, sample_menu):
        """
        Teste: Mensagem deve conter emojis.
        
        Arrange: Cardápio válido
        Act: Formatar
        Assert: Contém pelo menos um emoji
        """
        from src.bot.formatter import MenuFormatter
        
        formatter = MenuFormatter()
        message = formatter.format_meal(sample_menu, "Almoço")
        
        # Verificar presença de emojis comuns
        emojis = ["🍗", "🍚", "🥗", "🍹", "🍉", "🍽️"]
        has_emoji = any(emoji in message for emoji in emojis)
        assert has_emoji
    
    def test_format_date_returns_portuguese_format(self):
        """
        Teste: Deve formatar data em português "14/03 (Sex)".
        
        Arrange: Data 2026-03-14 (sexta-feira)
        Act: Formatar data
        Assert: Retorna "14/03 (Sex)" ou similar
        """
        from src.bot.formatter import MenuFormatter
        
        formatter = MenuFormatter()
        formatted = formatter.format_date("2026-03-14")
        
        assert isinstance(formatted, str)
        assert "14/03" in formatted
        # Deve conter abreviação do dia da semana
        assert "(" in formatted and ")" in formatted
    
    def test_format_full_menu_combines_almoco_and_janta(self, sample_menu):
        """
        Teste: Deve formatar cardápio completo (almoço + janta).
        
        Arrange: Dict com 'almoco' e 'janta'
        Act: Formatar cardápio completo
        Assert: Contém ambas as refeições
        """
        from src.bot.formatter import MenuFormatter
        
        menu_data = {
            "almoco": sample_menu,
            "janta": sample_menu
        }
        
        formatter = MenuFormatter()
        message = formatter.format_full_menu(menu_data, "2026-03-14")
        
        assert isinstance(message, str)
        assert "Almoço" in message or "ALMOÇO" in message
        assert "Jantar" in message or "JANTA" in message
    
    def test_format_meal_handles_empty_menu(self):
        """
        Teste: Deve lidar com cardápio vazio.
        
        Arrange: Dict vazio
        Act: Formatar
        Assert: Retorna mensagem de cardápio não disponível
        """
        from src.bot.formatter import MenuFormatter
        
        formatter = MenuFormatter()
        message = formatter.format_meal({}, "Almoço")
        
        assert isinstance(message, str)
        assert len(message) > 0
    
    def test_format_meal_handles_missing_fields(self):
        """
        Teste: Deve lidar com campos ausentes no cardápio.
        
        Arrange: Dict com apenas alguns campos
        Act: Formatar
        Assert: Não lança exceção e retorna string
        """
        from src.bot.formatter import MenuFormatter
        
        partial_menu = {
            "prato_principal": "Frango Grelhado",
            "acompanhamentos": ["Arroz"]
        }
        
        formatter = MenuFormatter()
        message = formatter.format_meal(partial_menu, "Almoço")
        
        assert isinstance(message, str)
        assert "Frango Grelhado" in message

    def test_format_meal_with_keyboard_returns_text_and_markup(self, sample_menu):
        """
        Teste: format_meal_with_keyboard deve retornar texto e markup.

        Arrange: Cardápio válido
        Act: Chamar format_meal_with_keyboard
        Assert: Retorna tupla (texto, InlineKeyboardMarkup)
        """
        from src.bot.formatter import MenuFormatter

        formatter = MenuFormatter()
        text, markup = formatter.format_meal_with_keyboard(sample_menu, "Almoço", "fav")

        assert isinstance(text, str)
        assert len(text) > 0
        assert markup is not None

    def test_format_meal_with_keyboard_has_favorite_button(self, sample_menu):
        """
        Teste: Markup deve conter botão de favoritar.

        Arrange: Cardápio válido
        Act: Chamar format_meal_with_keyboard
        Assert: Botão com texto contendo 'Favoritar'
        """
        from src.bot.formatter import MenuFormatter

        formatter = MenuFormatter()
        text, markup = formatter.format_meal_with_keyboard(sample_menu, "Almoço", "fav")

        buttons = markup.inline_keyboard[0]
        assert any("Favoritar" in btn.text for btn in buttons)

    def test_format_meal_with_keyboard_callback_data(self, sample_menu):
        """
        Teste: Botão deve ter callback_data correto.

        Arrange: Cardápio válido
        Act: Chamar format_meal_with_keyboard
        Assert: callback_data contém o prefixo e tipo de refeição
        """
        from src.bot.formatter import MenuFormatter

        formatter = MenuFormatter()
        text, markup = formatter.format_meal_with_keyboard(sample_menu, "Almoço", "fav")

        buttons = markup.inline_keyboard[0]
        fav_btn = next(btn for btn in buttons if "Favoritar" in btn.text)
        assert "fav:almoco" in fav_btn.callback_data

    def test_format_meal_with_keyboard_empty_menu(self):
        """
        Teste: Cardápio vazio não deve ter botão de favoritar.

        Arrange: Dict vazio
        Act: Chamar format_meal_with_keyboard
        Assert: Markup sem botões
        """
        from src.bot.formatter import MenuFormatter

        formatter = MenuFormatter()
        text, markup = formatter.format_meal_with_keyboard({}, "Almoço", "fav")

        assert len(markup.inline_keyboard) == 0

    def test_format_meal_with_keyboard_no_prato_principal(self):
        """
        Teste: Sem prato principal não deve ter botão de favoritar.

        Arrange: Cardápio sem prato_principal
        Act: Chamar format_meal_with_keyboard
        Assert: Markup sem botões
        """
        from src.bot.formatter import MenuFormatter

        menu = {"acompanhamentos": ["Arroz", "Feijão"]}
        formatter = MenuFormatter()
        text, markup = formatter.format_meal_with_keyboard(menu, "Almoço", "fav")

        assert len(markup.inline_keyboard) == 0

    def test_format_meal_with_keyboard_already_favorite(self, sample_menu):
        """
        Teste: Se prato já é favorito, botão deve mostrar 'Desfavoritar'.

        Arrange: Cardápio com prato já favoritado
        Act: Chamar format_meal_with_keyboard com is_favorite=True
        Assert: Botão com texto 'Desfavoritar'
        """
        from src.bot.formatter import MenuFormatter

        formatter = MenuFormatter()
        text, markup = formatter.format_meal_with_keyboard(
            sample_menu, "Almoço", "fav", is_favorite=True
        )

        buttons = markup.inline_keyboard[0]
        assert any("Desfavoritar" in btn.text for btn in buttons)
