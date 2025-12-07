"""
Telegram Approval Bot
Обрабатывает одобрение/отклонение новостей от админа
"""
import os
import json
from pathlib import Path
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')

# Путь к данным
DATA_DIR = Path(__file__).parent.parent / "data"
PENDING_FILE = DATA_DIR / "pending_posts.json"

class ApprovalBot:
    def __init__(self):
        self.pending_posts = self.load_pending()
    
    def load_pending(self):
        """Загружает ожидающие аппрува посты"""
        if PENDING_FILE.exists():
            with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_pending(self):
        """Сохраняет ожидающие посты"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(PENDING_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.pending_posts, f, ensure_ascii=False, indent=2)
    
    def add_pending(self, post_id: str, post_data: dict):
        """Добавляет пост в ожидание"""
        self.pending_posts[post_id] = post_data
        self.save_pending()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        await update.message.reply_text(
            "🤖 Telegram Approval Bot активен!\n\n"
            "Я буду отправлять новости для одобрения.\n"
            "Используй кнопки ✅/❌ для публикации или отклонения."
        )
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        pending_count = len(self.pending_posts)
        await update.message.reply_text(
            f"📊 Статус:\n\n"
            f"Ожидают одобрения: {pending_count} новостей"
        )
    
    async def approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатия кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        action, post_key = data.split('_', 1)
        
        if action == 'approve':
            # Публикуем в канал
            message_text = query.message.text
            
            # Убираем служебную информацию
            if "НОВАЯ НОВОСТЬ ДЛЯ АППРУВА:" in message_text:
                message_text = message_text.split("НОВАЯ НОВОСТЬ ДЛЯ АППРУВА:")[1].strip()
            
            # Публикуем
            try:
                telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                response = requests.post(telegram_url, json={
                    "chat_id": TELEGRAM_CHANNEL_ID,
                    "text": message_text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                })
                
                if response.status_code == 200:
                    await query.edit_message_text(
                        f"✅ ОПУБЛИКОВАНО\n\n{message_text}"
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Ошибка публикации\n\n{message_text}"
                    )
            except Exception as e:
                await query.edit_message_text(
                    f"❌ Ошибка: {e}\n\n{message_text}"
                )
        
        elif action == 'reject':
            # Отклоняем
            message_text = query.message.text
            await query.edit_message_text(
                f"❌ ОТКЛОНЕНО\n\n{message_text}"
            )
    
    def run(self):
        """Запускает бота"""
        if not TELEGRAM_BOT_TOKEN:
            print("❌ TELEGRAM_BOT_TOKEN не установлен")
            return
        
        if not TELEGRAM_ADMIN_ID:
            print("❌ TELEGRAM_ADMIN_ID не установлен")
            return
        
        print("=" * 60)
        print("🤖 Telegram Approval Bot")
        print("=" * 60)
        print(f"Admin ID: {TELEGRAM_ADMIN_ID}")
        print(f"Channel: {TELEGRAM_CHANNEL_ID}")
        print("Ожидаю команды...")
        
        # Создаём приложение
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("status", self.status))
        app.add_handler(CallbackQueryHandler(self.approve_callback))
        
        # Запускаем
        app.run_polling()

if __name__ == "__main__":
    bot = ApprovalBot()
    bot.run()
