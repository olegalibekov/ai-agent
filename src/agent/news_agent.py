"""
News Bot Agent
Главный агент: парсинг, фильтрация, публикация
"""
import os
import sys
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import anthropic
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

# Добавляем пути
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from rag_system import NewsRAG

class NewsAgent:
    def __init__(self):
        self.rag = NewsRAG()
        self.mcp_url = "http://localhost:8002"
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # RSS источники
        self.news_sources = [
            {
                "name": "TechCrunch",
                "url": "https://techcrunch.com/feed/",
                "category": "tech"
            },
            {
                "name": "Hacker News",
                "url": "https://news.ycombinator.com/rss",
                "category": "tech"
            },
            {
                "name": "BBC News",
                "url": "http://feeds.bbci.co.uk/news/rss.xml",
                "category": "world"
            }
        ]
    
    def initialize(self):
        """Инициализация"""
        print("🔧 Инициализация News Agent...")
        self.rag.initialize()
        print("✓ News Agent готов")
    
    def fetch_news(self, hours: int = 1) -> List[Dict]:
        """Парсит новости из RSS за последний час"""
        print(f"\n📡 Парсинг новостей за последний {hours} час(а)...")
        
        all_news = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        for source in self.news_sources:
            try:
                print(f"  - {source['name']}...", end=" ")
                
                feed = feedparser.parse(source['url'])
                
                count = 0
                for entry in feed.entries:
                    # Проверяем время публикации
                    if hasattr(entry, 'published_parsed'):
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed'):
                        pub_date = datetime(*entry.updated_parsed[:6])
                    else:
                        pub_date = datetime.utcnow()
                    
                    if pub_date >= cutoff_time:
                        news_item = {
                            "title": entry.get('title', ''),
                            "description": entry.get('summary', '')[:300],
                            "url": entry.get('link', ''),
                            "source": source['name'],
                            "category": source['category'],
                            "published_at": pub_date.isoformat()
                        }
                        all_news.append(news_item)
                        count += 1
                
                print(f"✓ {count} новостей")
            except Exception as e:
                print(f"✗ Ошибка: {e}")
        
        print(f"\n✓ Всего найдено: {len(all_news)} новостей")
        return all_news
    
    def filter_duplicates(self, news_items: List[Dict]) -> List[Dict]:
        """Фильтрует дубликаты через RAG"""
        print("\n🔍 Проверка дубликатов...")
        
        unique_news = []
        
        for item in news_items:
            duplicate = self.rag.check_duplicate(
                item['title'], 
                item['description'],
                similarity_threshold=0.85
            )
            
            if duplicate:
                print(f"  ⚠️ Дубликат: {item['title'][:50]}...")
                print(f"     Похоже на: {duplicate['title'][:50]}... (similarity: {duplicate['similarity']:.2f})")
            else:
                unique_news.append(item)
        
        print(f"✓ Уникальных новостей: {len(unique_news)}")
        return unique_news
    
    def ai_filter_and_format(self, news_items: List[Dict]) -> List[Dict]:
        """AI фильтрует и форматирует новости"""
        if not self.anthropic_api_key:
            print("⚠️ ANTHROPIC_API_KEY не установлен, пропускаю AI фильтрацию")
            return news_items[:3]  # Берём топ-3
        
        print("\n🤖 AI фильтрация и форматирование...")
        
        # Формируем список для анализа
        news_list = "\n\n".join([
            f"{i+1}. {item['title']}\n   {item['description'][:200]}\n   Источник: {item['source']}"
            for i, item in enumerate(news_items[:10])  # Топ-10 для анализа
        ])
        
        prompt = f"""Ты - редактор новостного Telegram канала о технологиях и бизнесе.

Вот новости за последний час:

{news_list}

Задача:
1. Выбери ТОП-3 самые интересные и важные новости
2. Для каждой создай пост для Telegram (100-150 слов)
3. Используй эмодзи, делай читабельно
4. Добавь хештеги

Формат ответа (JSON):
[
  {{
    "original_index": 1,
    "formatted_text": "📱 Apple анонсировала...",
    "hashtags": ["#Apple", "#Tech"]
  }}
]

Верни ТОЛЬКО JSON массив, без пояснений."""

        try:
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Парсим JSON (убираем ```json если есть)
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            import json
            filtered = json.loads(response_text)
            
            # Добавляем форматированный текст к оригинальным новостям
            result = []
            for item in filtered[:3]:  # Топ-3
                idx = item['original_index'] - 1
                if 0 <= idx < len(news_items):
                    news = news_items[idx].copy()
                    news['formatted_text'] = item['formatted_text']
                    news['hashtags'] = item.get('hashtags', [])
                    result.append(news)
            
            print(f"✓ AI отобрал и отформатировал {len(result)} новостей")
            return result
        
        except Exception as e:
            print(f"⚠️ Ошибка AI: {e}")
            # Fallback: берём первые 3
            return news_items[:3]
    
    def check_can_post(self) -> Dict:
        """Проверяет можно ли постить через MCP"""
        try:
            response = requests.get(f"{self.mcp_url}/can-post")
            return response.json()
        except Exception as e:
            print(f"⚠️ Ошибка MCP: {e}")
            return {"can_post": False, "reason": "MCP недоступен"}
    
    def save_to_mcp(self, news_item: Dict) -> str:
        """Сохраняет пост в MCP"""
        try:
            response = requests.post(f"{self.mcp_url}/posts", json=news_item)
            result = response.json()
            return result['post_id']
        except Exception as e:
            print(f"⚠️ Ошибка сохранения в MCP: {e}")
            return None
    
    def send_to_telegram(self, text: str, url: str, news_item: Dict) -> bool:
        """Отправляет в Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("\n" + "═" * 60)
            print("📱 TELEGRAM POST (СИМУЛЯЦИЯ)")
            print("═" * 60)
            print("\n⚠️  Токены не установлены, показываю что БЫЛО БЫ опубликовано:\n")
            print("─" * 60)
            print(text)
            print(f"\n🔗 Читать полностью: {url}")
            print("─" * 60)
            print("\n💡 Для реальной публикации добавь:")
            print("   export TELEGRAM_BOT_TOKEN='your_token'")
            print("   export TELEGRAM_CHAT_ID='@your_channel'")
            print("   export TELEGRAM_ADMIN_ID='your_user_id'  # Для аппрува")
            print("═" * 60)
            return True
        
        try:
            # Отправляем админу на аппрув
            admin_id = os.getenv('TELEGRAM_ADMIN_ID')
            
            if admin_id:
                return self._send_for_approval(text, url, news_item, admin_id)
            else:
                # Прямая публикация без аппрува
                return self._publish_to_channel(text, url)
        
        except Exception as e:
            print(f"✗ Ошибка отправки: {e}")
            return False
    
    def _send_for_approval(self, text: str, url: str, news_item: Dict, admin_id: str) -> bool:
        """Отправляет новость админу для аппрува"""
        try:
            telegram_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            # Формируем сообщение с кнопками
            preview_text = f"📰 НОВАЯ НОВОСТЬ ДЛЯ АППРУВА:\n\n{text}\n\n🔗 {url}"
            
            # Inline кнопки для аппрува
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Опубликовать", "callback_data": f"approve_{news_item.get('title', '')[:20]}"},
                        {"text": "❌ Отклонить", "callback_data": f"reject_{news_item.get('title', '')[:20]}"}
                    ]
                ]
            }
            
            response = requests.post(telegram_url, json={
                "chat_id": admin_id,
                "text": preview_text,
                "parse_mode": "HTML",
                "reply_markup": keyboard
            })
            
            if response.status_code == 200:
                print("✓ Отправлено админу на аппрув")
                print(f"  Ожидается решение: ✅ Опубликовать или ❌ Отклонить")
                return True
            else:
                print(f"✗ Ошибка отправки админу: {response.text}")
                return False
        
        except Exception as e:
            print(f"✗ Ошибка аппрува: {e}")
            return False
    
    def _publish_to_channel(self, text: str, url: str) -> bool:
        """Публикует напрямую в канал"""
        try:
            telegram_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            full_text = f"{text}\n\n🔗 Читать: {url}"
            
            response = requests.post(telegram_url, json={
                "chat_id": self.telegram_chat_id,
                "text": full_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            })
            
            if response.status_code == 200:
                print("✓ Опубликовано в канал")
                return True
            else:
                print(f"✗ Ошибка публикации: {response.text}")
                return False
        
        except Exception as e:
            print(f"✗ Ошибка публикации: {e}")
            return False
    
    def run(self):
        """Главный цикл"""
        print("\n" + "=" * 60)
        print("🤖 NEWS BOT AGENT")
        print("=" * 60)
        
        # 1. Парсинг новостей
        news_items = self.fetch_news(hours=1)
        
        if not news_items:
            print("\n❌ Нет свежих новостей")
            return
        
        # 2. Фильтрация дубликатов (RAG)
        unique_news = self.filter_duplicates(news_items)
        
        if not unique_news:
            print("\n❌ Все новости - дубликаты")
            return
        
        # 3. AI фильтрация и форматирование
        filtered_news = self.ai_filter_and_format(unique_news)
        
        if not filtered_news:
            print("\n❌ AI не отобрал новости")
            return
        
        # 4. Проверка лимитов (MCP)
        can_post = self.check_can_post()
        
        if not can_post.get('can_post'):
            print(f"\n⚠️ Нельзя постить: {can_post.get('reason')}")
            return
        
        # 5. Публикация
        print(f"\n📤 Публикация {len(filtered_news)} новостей...")
        
        for i, news in enumerate(filtered_news, 1):
            print(f"\n[{i}/{len(filtered_news)}] {news['title']}")
            
            # Сохраняем в MCP
            post_id = self.save_to_mcp(news)
            if post_id:
                print(f"  ✓ Сохранено в MCP: {post_id}")
            
            # Отправляем в Telegram
            text = news.get('formatted_text', news['title'])
            self.send_to_telegram(text, news['url'], news)
            
            # Добавляем в RAG индекс
            self.rag.add_news(news)
            print(f"  ✓ Добавлено в RAG индекс")
        
        print("\n" + "=" * 60)
        print("✅ Готово!")
        print("=" * 60)

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    agent = NewsAgent()
    agent.initialize()
    agent.run()
