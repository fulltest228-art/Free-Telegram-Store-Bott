import flask
from datetime import datetime
import logging
from flask import Flask, request
from telebot import types, TeleBot
import os
from InDMDevDB import CreateTables, CreateDatas, GetDataFromDB
from purchase import UserOperations
from InDMCategories import CategoriesDatas
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Flask connection
flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Bot connection
webhook_url = os.getenv('WEBHOOK_URL')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
store_currency = os.getenv('STORE_CURRENCY', 'USD')

if not webhook_url or not bot_token:
    logger.error("Missing required environment variables: WEBHOOK_URL or TELEGRAM_BOT_TOKEN")
    exit(1)

bot = TeleBot(bot_token, threaded=False)

# Set up webhook
try:
    bot.remove_webhook()
    bot.set_webhook(url=f"{webhook_url}/webhook")
    logger.info(f"Webhook set successfully to {webhook_url}/webhook")
except Exception as e:
    logger.error(f"Failed to set webhook: {e}")
    exit(1)

# Process webhook calls
@flask_app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST' and request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    logger.warning(f"Invalid request to /webhook: method={request.method}, content-type={request.headers.get('content-type')}")
    return '', 400

@flask_app.route('/', methods=['HEAD', 'GET'])
def health_check():
    logger.info(f"Health check: {request.method}")
    return '', 200

# Main keyboard
def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.row_width = 2
    key1 = types.KeyboardButton("Shop Items 🛒")
    key2 = types.KeyboardButton("My Orders 🛍")
    key3 = types.KeyboardButton("Support 📞")
    keyboard.add(key1)
    keyboard.add(key2, key3)
    return keyboard

# Callback handler
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        if call.data.startswith("getcats_"):
            input_catees = call.data.replace('getcats_', '')
            CategoriesDatas.get_category_products(call.message, input_catees)
        elif call.data.startswith("getproduct_"):
            input_cate = call.data.replace('getproduct_', '')
            UserOperations.purchase_a_products(call.message, input_cate)
    except Exception as e:
        logger.error(f"Callback error: {e}")

# Start message
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    CreateDatas.add_user(chat_id, message.from_user.username)
    bot.send_message(chat_id, "Welcome to the store! Use /shop to browse.", reply_markup=create_main_keyboard())

if __name__ == '__main__':
    try:
      logger.info("Starting Flask application...")
      flask_app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
    except Exception as e:
        logger.error(f"Error starting Flask application: {e}")
        exit(1)
