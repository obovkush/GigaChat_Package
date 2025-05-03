import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from gigachat.client import GigaChatSyncClient
from models import db, ChatHistory
import markdown2  # Добавляем импорт markdown2

# Загрузка переменных окружения из .env файла
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db.init_app(app)

# Создание таблиц базы данных
with app.app_context():
    db.create_all()

class GigaChatPackageClient:
    def __init__(self):
        self.api_key = os.getenv('GIGACHAT_API_KEY')
        if not self.api_key:
            raise ValueError("API ключ не найден. Пожалуйста, создайте файл .env и добавьте GIGACHAT_API_KEY")

        # Инициализация клиента GigaChat с отключенной проверкой SSL и правильным scope
        self.client = GigaChatSyncClient(
            credentials=self.api_key,
            verify_ssl=False,
            scope="GIGACHAT_API_PERS"
        )

    def send_message(self, message):
        """Отправляет сообщение в GigaChat и возвращает ответ"""
        try:
            # Формируем сообщение в правильном формате
            chat_message = {
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            }
            response = self.client.chat(chat_message)
            # Преобразуем Markdown в HTML
            html_response = markdown2.markdown(response.choices[0].message.content)
            return html_response
        except Exception as e:
            print(f"Ошибка при отправке запроса: {e}")
            return None

# Создаем экземпляр клиента
giga_client = GigaChatPackageClient()

@app.route('/')
def index():
    # Получаем историю сообщений из базы данных
    history = ChatHistory.query.order_by(ChatHistory.timestamp.desc()).limit(50).all()
    # Преобразуем Markdown в HTML для каждого сообщения
    for entry in history:
        entry.ai_response = markdown2.markdown(entry.ai_response)
    return render_template('index.html', history=history)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message')

    if not message:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400

    # Получаем ответ от GigaChat
    response = giga_client.send_message(message)

    if response:
        # Сохраняем сообщение и ответ в базу данных
        chat_entry = ChatHistory(
            user_message=message,
            ai_response=response
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({'response': response})
    else:
        return jsonify({'error': 'Ошибка при получении ответа от GigaChat'}), 500

if __name__ == "__main__":
    app.run(debug=True)
