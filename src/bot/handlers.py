"""Handlers dos comandos do bot."""

import os
import tempfile
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from src.scraper.menu_extractor import MenuExtractor
from src.scraper.pdf_parser import PDFParser
from src.scraper.table_menu_extractor import TableMenuExtractor


class BotHandlers:
    """Processa comandos do Telegram, integrando cache, usuários e formatador."""
    
    def __init__(self, menu_cache, user_manager, formatter, auto_updater=None):
        self.cache = menu_cache
        self.users = user_manager
        self.formatter = formatter
        self.auto_updater = auto_updater
    
    async def _send_meal_for_today(self, update: Update, meal_type: str, meal_key: str):
        """Busca o cardápio de hoje no cache e responde ao usuário."""
        if not update.message:
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        menu_data = self.cache.get_menu(today)
        
        if not menu_data or meal_key not in menu_data:
            await update.message.reply_text(
                f"❌ Cardápio do {meal_type.lower()} não disponível para hoje.",
                parse_mode="Markdown"
            )
            return
        
        formatted_message = self.formatter.format_meal(menu_data[meal_key], meal_type)
        await update.message.reply_text(formatted_message, parse_mode="Markdown")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inscreve o usuário e envia boas-vindas."""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        self.users.add_user(user_id)
        
        welcome_message = (
            f"👋 Olá, *{user_name}*!\n\n"
            "Bem-vindo ao *Bot do RU UFCA*!\n\n"
            "🔔 Você foi inscrito para receber notificações automáticas dos cardápios.\n\n"
            "📋 *Comandos disponíveis:*\n"
            "/almoco - Cardápio do almoço de hoje\n"
            "/janta - Cardápio da janta de hoje\n"
            "/semana - Cardápio da semana\n"
            "/parar - Parar de receber notificações\n"
            "/help - Ajuda e lista de comandos\n\n"
            "Bom apetite! 🍽️"
        )
        
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
    
    async def almoco_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra o cardápio do almoço de hoje."""
        await self._send_meal_for_today(update, "Almoço", "almoco")
    
    async def janta_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra o cardápio da janta de hoje."""
        await self._send_meal_for_today(update, "Jantar", "janta")
    
    async def semana_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra o cardápio completo da semana."""
        weekly_menu = self.cache.get_weekly_menu()
        
        if not weekly_menu:
            await update.message.reply_text(
                "❌ Cardápio da semana não disponível.",
                parse_mode="Markdown"
            )
            return
        
        messages = ["📅 *CARDÁPIO DA SEMANA*\n"]
        
        for date_str in sorted(weekly_menu.keys()):
            formatted_date = self.formatter.format_date(date_str)
            day_menu = weekly_menu[date_str]
            
            messages.append(f"\n{'─' * 25}")
            messages.append(f"📆 *{formatted_date}*\n")
            
            if "almoco" in day_menu:
                messages.append(self.formatter.format_meal(day_menu["almoco"], "Almoço"))
            
            if "janta" in day_menu:
                messages.append("")
                messages.append(self.formatter.format_meal(day_menu["janta"], "Jantar"))
        
        full_message = "\n".join(messages)
        
        # Telegram limita mensagens a 4096 caracteres
        if len(full_message) > 4000:
            await update.message.reply_text(
                "📅 *CARDÁPIO DA SEMANA*\n\n"
                "⚠️ Cardápio muito extenso. Use /almoco ou /janta para ver o cardápio de hoje.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(full_message, parse_mode="Markdown")
    
    async def parar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove o usuário das notificações."""
        user_id = update.effective_user.id
        
        if not self.users.is_subscribed(user_id):
            await update.message.reply_text(
                "ℹ️ Você não está inscrito para receber notificações.",
                parse_mode="Markdown"
            )
            return
        
        self.users.remove_user(user_id)
        
        await update.message.reply_text(
            "✅ Você foi removido da lista de notificações.\n\n"
            "Para voltar a receber notificações, use o comando /start",
            parse_mode="Markdown"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista todos os comandos disponíveis."""
        help_message = (
            "📋 *COMANDOS DISPONÍVEIS*\n\n"
            "/start - Iniciar bot e receber notificações\n"
            "/almoco - Ver cardápio do almoço de hoje\n"
            "/janta - Ver cardápio da janta de hoje\n"
            "/semana - Ver cardápio da semana completa\n"
            "/parar - Parar de receber notificações\n"
            "/atualizar - Forçar busca de cardápio (admin)\n"
            "/help - Exibir esta mensagem de ajuda\n\n"
            "💡 *Dica:* Você receberá notificações automáticas "
            "nos horários do almoço e janta!"
        )
        
        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def atualizar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Força a atualização do cardápio a partir do site da UFCA. Apenas admin."""
        user_id = update.effective_user.id
        admin_id = int(os.environ.get("ADMIN_CHAT_ID", "0"))

        if user_id != admin_id:
            await update.message.reply_text(
                "⛔ Apenas o administrador pode usar este comando.",
                parse_mode="Markdown"
            )
            return

        if not self.auto_updater:
            await update.message.reply_text(
                "❌ Atualização automática não está configurada.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text("🔄 Buscando cardápio atualizado no site da UFCA...", parse_mode="Markdown")

        success = await self.auto_updater.update_menu_from_web()

        if success:
            today = datetime.now().strftime("%Y-%m-%d")
            menu = self.cache.get_menu(today)
            if menu:
                await update.message.reply_text(
                    f"✅ Cardápio atualizado com sucesso!\n\n"
                    f"Use /almoco ou /janta para ver o cardápio de hoje.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    "✅ Cardápios salvos, mas nenhum para hoje.\n"
                    "Use /semana para ver o cardápio da semana.",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Falha ao atualizar cardápio. Verifique os logs ou tente novamente mais tarde.",
                parse_mode="Markdown"
            )

    async def pdf_upload_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Recebe um PDF de cardápio enviado pelo admin e salva no cache.

        Só o admin (ADMIN_CHAT_ID) pode usar. O arquivo é baixado,
        processado pelo MenuExtractor e descartado em seguida.
        """
        user_id = update.effective_user.id
        admin_id = int(os.environ.get("ADMIN_CHAT_ID", "0"))

        if user_id != admin_id:
            await update.message.reply_text(
                "⛔ Você não tem permissão para enviar cardápios. "
                "Apenas o admin pode fazer upload de PDFs.",
                parse_mode="Markdown"
            )
            return

        document = update.message.document
        is_pdf = (
            document.file_name.lower().endswith(".pdf")
            or document.mime_type == "application/pdf"
        )
        if not is_pdf:
            await update.message.reply_text(
                "❌ Formato inválido. Por favor, envie um arquivo PDF.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text("⏳ Processando PDF...", parse_mode="Markdown")

        tmp_path = None
        try:
            tg_file = await document.get_file()
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)

            # Extrair tabelas do PDF (método preferido)
            parser = PDFParser(tmp_path)
            tables = parser.extract_tables()
            
            if tables:
                # Usar extração baseada em tabelas (mais precisa)
                extractor = TableMenuExtractor(tables)
                weekly_menus = extractor.extract_menus()
            else:
                # Fallback: usar extração por texto
                text = parser.extract_text()
                text_extractor = MenuExtractor(text)
                weekly_menus = text_extractor.extract_menus()

            for date_str, menu_data in weekly_menus.items():
                self.cache.save_menu(date_str, menu_data)

            await update.message.reply_text(
                f"✅ PDF processado com sucesso!\n"
                f"📅 *{len(weekly_menus)} dias* de cardápio salvos no cache.",
                parse_mode="Markdown"
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Erro ao processar o PDF: {e}",
                parse_mode="Markdown"
            )

        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
