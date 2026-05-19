"""Formata cardápios em mensagens com emojis para o Telegram."""

from datetime import datetime
from typing import Dict, Any, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class MenuFormatter:
    """Transforma dados de cardápio em texto formatado para o Telegram."""
    
    EMOJIS = {
        "prato_principal": "🍗",
        "vegetariano": "🥗",
        "acompanhamentos": "🍚",
        "saladas": "🥬",
        "suco": "🍹",
        "sobremesa": "🍉",
        "meal": "🍽️"
    }
    
    # Dias da semana abreviados em português
    WEEKDAYS = {
        0: "Seg",
        1: "Ter",
        2: "Qua",
        3: "Qui",
        4: "Sex",
        5: "Sáb",
        6: "Dom"
    }
    
    FIELD_LABELS = {
        "prato_principal": "Principal",
        "vegetariano": "Vegetariano",
        "acompanhamentos": "Acompanhamentos",
        "saladas": "Saladas",
        "suco": "Suco",
        "sobremesa": "Sobremesa"
    }
    
    def _format_field(self, field_key: str, field_value: Any) -> str:
        """Retorna uma linha formatada com emoji, label e valor do campo."""
        emoji = self.EMOJIS.get(field_key, "")
        label = self.FIELD_LABELS.get(field_key, field_key.replace("_", " ").title())
        
        # Listas viram string separada por vírgulas
        if isinstance(field_value, list):
            value_str = ", ".join(field_value)
        else:
            value_str = str(field_value)
        
        return f"{emoji} *{label}:* {value_str}"
    
    def format_meal(self, menu_data: Dict[str, Any], meal_type: str) -> str:
        """Monta o bloco de texto de uma refeição (almoço ou jantar)."""
        if not menu_data:
            return f"{self.EMOJIS['meal']} *{meal_type}*\n\nCardápio não disponível."
        
        lines = [f"{self.EMOJIS['meal']} *{meal_type.upper()}*\n"]
        
        field_order = ["prato_principal", "vegetariano", "acompanhamentos", "saladas", "suco", "sobremesa"]
        
        for field_key in field_order:
            if field_key in menu_data:
                lines.append(self._format_field(field_key, menu_data[field_key]))
        
        return "\n".join(lines)
    
    def format_date(self, iso_date: str) -> str:
        """Converte "2026-03-14" em "14/03 (Sex)"."""
        date_obj = datetime.fromisoformat(iso_date)
        day = date_obj.day
        month = date_obj.month
        weekday = self.WEEKDAYS[date_obj.weekday()]
        
        return f"{day:02d}/{month:02d} ({weekday})"
    
    def format_full_menu(self, menu_data: Dict[str, Any], iso_date: str) -> str:
        """Monta almoço + jantar de um dia em uma única mensagem."""
        formatted_date = self.format_date(iso_date)
        lines = [f"📅 *Cardápio de {formatted_date}*\n"]
        
        if "almoco" in menu_data:
            lines.append(self.format_meal(menu_data["almoco"], "Almoço"))
        
        lines.append("\n" + "─" * 25 + "\n")
        
        if "janta" in menu_data:
            lines.append(self.format_meal(menu_data["janta"], "Jantar"))
        
        return "\n".join(lines)

    def format_meal_with_keyboard(
        self,
        menu_data: Dict[str, Any],
        meal_type: str,
        callback_prefix: str,
        is_favorite: bool = False,
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Monta o bloco de texto de uma refeição com botão inline de favoritar."""
        text = self.format_meal(menu_data, meal_type)

        buttons = []
        prato = menu_data.get("prato_principal")
        if prato:
            meal_key = meal_type.lower().replace("ç", "c").replace("ã", "a")
            if is_favorite:
                btn_text = f"☆ Desfavoritar {prato}"
                callback_data = f"unfav:{meal_key}"
            else:
                btn_text = f"☆ Favoritar {prato}"
                callback_data = f"fav:{meal_key}"
            buttons.append(InlineKeyboardButton(btn_text, callback_data=callback_data))

        keyboard = [buttons] if buttons else []
        return text, InlineKeyboardMarkup(keyboard)
