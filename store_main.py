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
admin_ids = os.getenv('ADMIN_IDS', '987654321').split(',')  # Comma-separated list, default to your ID

if not webhook_url or not bot_token:
    logger.error("Missing required environment variables: WEBHOOK_URL or TELEGRAM_BOT_TOKEN")
    exit(1)

bot = TeleBot(bot_token, threaded=False)

# Store user states (e.g., waiting for product details)
user_states = {}

# Set up webhook only if needed
try:
    webhook_info = bot.get_webhook_info()
    if webhook_info.url != f"{webhook_url}/webhook":
        bot.remove_webhook()
        bot.set_webhook(url=f"{webhook_url}/webhook")
        logger.info(f"Webhook set successfully to {webhook_url}/webhook")
    else:
        logger.info(f"Webhook already set to {webhook_url}/webhook")
except Exception as e:
    logger.error(f"Failed to manage webhook: {e}")
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

# Admin keyboard
def create_admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.row_width = 2
    key1 = types.KeyboardButton("Add Item 📦")
    key2 = types.KeyboardButton("Edit Item ✏️")
    key3 = types.KeyboardButton("Back 🔙")
    keyboard.add(key1, key2, key3)
    return keyboard

# Callback handler
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        logger.info(f"Callback received: {call.data}")
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
    username = message.from_user.username
    if CreateDatas.add_user(chat_id, username):
        bot.send_message(chat_id, "Welcome to the store! Use /shop to browse.", reply_markup=create_main_keyboard())
        logger.info(f"Sent welcome to {username} (ID: {chat_id})")
    else:
        bot.send_message(chat_id, "Failed to register you. Contact support.", reply_markup=create_main_keyboard())
        logger.error(f"Failed to add user {username} (ID: {chat_id})")

# Admin command to enter admin mode
@bot.message_handler(commands=['admin'])
def enter_admin_mode(message):
    chat_id = message.chat.id
    username = message.from_user.username
    if str(chat_id) in admin_ids and CreateDatas.add_admin(chat_id, username):
        bot.send_message(chat_id, "Admin mode activated. Choose an option:", reply_markup=create_admin_keyboard())
        logger.info(f"Admin mode activated for {username} (ID: {chat_id})")
    else:
        bot.send_message(chat_id, "You are not an admin.", reply_markup=create_main_keyboard())
        logger.warning(f"Non-admin {username} (ID: {chat_id}) tried to enter admin mode")

# Handle admin actions
@bot.message_handler(func=lambda message: message.text in ["Add Item 📦", "Edit Item ✏️", "Back 🔙"])
def handle_admin_action(message):
    chat_id = message.chat.id
    text = message.text
    if text == "Add Item 📦":
        user_states[chat_id] = "awaiting_product_details"
        bot.send_message(chat_id, "Send product details (name,price,quantity), e.g., TestProduct,10,5")
    elif text == "Edit Item ✏️":
        user_states[chat_id] = "awaiting_product_id"
        bot.send_message(chat_id, "Send product number to edit")
    elif text == "Back 🔙":
        del user_states[chat_id]
        bot.send_message(chat_id, "Returning to main menu.", reply_markup=create_main_keyboard())

# Handle text input for admin actions
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text
    if chat_id in user_states:
        if user_states[chat_id] == "awaiting_product_details":
            try:
                name, price, quantity = text.split(',')
                price = int(price)
                quantity = int(quantity)
                if CreateDatas.add_product(chat_id, message.from_user.username, name, "", price, quantity, "Default Category"):
                    bot.send_message(chat_id, f"Product '{name}' added successfully! Price: {price}, Quantity: {quantity}")
                    logger.info(f"Product '{name}' added by {message.from_user.username}")
                else:
                    bot.send_message(chat_id, "Failed to add product. Check logs.")
                    logger.error(f"Failed to add product '{name}' by {message.from_user.username}")
                del user_states[chat_id]
            except ValueError:
                bot.send_message(chat_id, "Invalid format. Use: name,price,quantity (e.g., TestProduct,10,5)")
                logger.warning(f"Invalid input format from {message.from_user.username}: {text}")
        elif user_states[chat_id] == "awaiting_product_id":
            try:
                product_id = int(text)
                # Placeholder for edit logic
                bot.send_message(chat_id, f"Editing product {product_id}. Send new details (name,price,quantity).")
                user_states[chat_id] = "awaiting_edit_details"
            except ValueError:
                bot.send_message(chat_id, "Invalid product number. Send a number.")
                logger.warning(f"Invalid product ID from {message.from_user.username}: {text}")
        elif user_states[chat_id] == "awaiting_edit_details":
            try:
                name, price, quantity = text.split(',')
                price = int(price)
                quantity = int(quantity)
                # Add edit logic here (e.g., UpdateData.update_product_quantity)
                bot.send_message(chat_id, f"Product {name} updated! Price: {price}, Quantity: {quantity}")
                del user_states[chat_id]
            except ValueError:
                bot.send_message(chat_id, "Invalid format. Use: name,price,quantity")
    elif text == "/shop":
        bot.send_message(message.chat.id, "Shop coming soon!", reply_markup=create_main_keyboard())
    elif text.startswith("admin,"):
        enter_admin_mode(message)

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application...")
        flask_app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
    except Exception as e:
        logger.error(f"Error starting Flask application: {e}")
        exit(1)
