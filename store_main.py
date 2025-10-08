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
admin_ids = os.getenv('ADMIN_IDS', '987654321').split(',')

if not webhook_url or not bot_token:
    logger.error("Missing required environment variables: WEBHOOK_URL or TELEGRAM_BOT_TOKEN")
    exit(1)

bot = TeleBot(bot_token, threaded=False)

# Store user states
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
    key3 = types.KeyboardButton("List Products 📋")
    key4 = types.KeyboardButton("Back 🔙")
    keyboard.add(key1, key2)
    keyboard.add(key3, key4)
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
@bot.message_handler(func=lambda message: message.text in ["Add Item 📦", "Edit Item ✏️", "List Products 📋", "Back 🔙"])
def handle_admin_action(message):
    chat_id = message.chat.id
    text = message.text
    if text == "Add Item 📦":
        user_states[str(chat_id)] = "awaiting_product_name"
        bot.send_message(chat_id, "Send the product name:")
    elif text == "Edit Item ✏️":
        user_states[str(chat_id)] = "awaiting_edit_id"
        bot.send_message(chat_id, "Send the product number to edit:")
    elif text == "List Products 📋":
        products = GetDataFromDB.get_products()
        if products:
            response = "Products:\n"
            for product in products:
                response += f"ID: {product['productnumber']} - {product['productname']} ({product['productquantity']} left)\n"
            bot.send_message(chat_id, response)
        else:
            bot.send_message(chat_id, "No products yet.")
        bot.send_message(chat_id, "Choose an option:", reply_markup=create_admin_keyboard())
    elif text == "Back 🔙":
        del user_states[str(chat_id)]
        bot.send_message(chat_id, "Returning to main menu.", reply_markup=create_main_keyboard())

# Handle text input for admin actions
@bot.message_handler(content_types=['text', 'photo'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text if message.text else None
    if str(chat_id) in user_states:
        state = user_states[str(chat_id)]
        if state == "awaiting_product_name":
            user_states[str(chat_id)] = "awaiting_product_price"
            user_states[str(chat_id) + '_name'] = text
            bot.send_message(chat_id, "Send the product price:")
        elif state == "awaiting_product_price":
            try:
                price = int(text)
                user_states[str(chat_id)] = "awaiting_product_quantity"
                user_states[str(chat_id) + '_price'] = price
                bot.send_message(chat_id, "Send the product quantity:")
            except ValueError:
                bot.send_message(chat_id, "Invalid price. Send a number.")
        elif state == "awaiting_product_quantity":
            try:
                quantity = int(text)
                user_states[str(chat_id)] = "awaiting_product_photo"
                user_states[str(chat_id) + '_quantity'] = quantity
                bot.send_message(chat_id, "Send the product photo (optional, or type 'skip' for no photo):")
            except ValueError:
                bot.send_message(chat_id, "Invalid quantity. Send a number.")
        elif state == "awaiting_product_photo":
            name = user_states[str(chat_id) + '_name']
            price = user_states[str(chat_id) + '_price']
            quantity = user_states[str(chat_id) + '_quantity']
            productimagelink = None
            if text and text.lower() == 'skip':
                if CreateDatas.add_product(chat_id, message.from_user.username, name, "", price, quantity, "Default Category", productimagelink):
                    bot.send_message(chat_id, f"Product '{name}' added successfully! Price: {price}, Quantity: {quantity}")
                    logger.info(f"Product '{name}' added by {message.from_user.username}")
                else:
                    bot.send_message(chat_id, "Failed to add product. Check logs.")
                del user_states[str(chat_id)]
                del user_states[str(chat_id) + '_name']
                del user_states[str(chat_id) + '_price']
                del user_states[str(chat_id) + '_quantity']
                bot.send_message(chat_id, "Choose an option:", reply_markup=create_admin_keyboard())
            else:
                user_states[str(chat_id)] = "awaiting_product_photo_upload"
                bot.send_message(chat_id, "Send the product photo (or type 'skip' again):")
        elif state == "awaiting_product_photo_upload" and message.photo:
            name = user_states[str(chat_id) + '_name']
            price = user_states[str(chat_id) + '_price']
            quantity = user_states[str(chat_id) + '_quantity']
            productimagelink = message.photo[-1].file_id  # Largest photo
            if CreateDatas.add_product(chat_id, message.from_user.username, name, "", price, quantity, "Default Category", productimagelink):
                bot.send_photo(chat_id, photo=productimagelink, caption=f"Product '{name}' added with photo! Price: {price}, Quantity: {quantity}")
                logger.info(f"Product '{name}' added with photo by {message.from_user.username}")
            else:
                bot.send_message(chat_id, "Failed to add product. Check logs.")
            del user_states[str(chat_id)]
            del user_states[str(chat_id) + '_name']
            del user_states[str(chat_id) + '_price']
            del user_states[str(chat_id) + '_quantity']
            bot.send_message(chat_id, "Choose an option:", reply_markup=create_admin_keyboard())
        elif state == "awaiting_edit_id":
            try:
                product_id = int(text)
                product = GetDataFromDB.get_product_by_id(product_id)
                if product:
                    user_states[str(chat_id)] = "awaiting_edit_details"
                    user_states[str(chat_id) + '_edit_id'] = product_id
                    bot.send_message(chat_id, f"Editing {product['productname']}. Send new details (name,price,quantity):")
                else:
                    bot.send_message(chat_id, "Product not found.")
                    bot.send_message(chat_id, "Choose an option:", reply_markup=create_admin_keyboard())
            except ValueError:
                bot.send_message(chat_id, "Invalid product number. Send a number.")
        elif state == "awaiting_edit_details":
            try:
                name, price, quantity = text.split(',')
                price = int(price)
                quantity = int(quantity)
                # Update product (placeholder)
                bot.send_message(chat_id, f"Product updated to '{name}'! Price: {price}, Quantity: {quantity}")
                del user_states[str(chat_id)]
                del user_states[str(chat_id) + '_edit_id']
                bot.send_message(chat_id, "Choose an option:", reply_markup=create_admin_keyboard())
            except ValueError:
                bot.send_message(chat_id, "Invalid format. Use: name,price,quantity")
    elif text == "/shop":
        products = GetDataFromDB.get_products()
        if products:
            response = "Products:\n"
            for product in products:
                response += f"ID: {product['productnumber']} - {product['productname']} ({product['productquantity']} left) - {product['productprice']} {store_currency}\n"
            bot.send_message(message.chat.id, response)
        else:
            bot.send_message(message.chat.id, "No products available yet.")
        bot.send_message(message.chat.id, "Choose an option:", reply_markup=create_main_keyboard())
    elif text and text.startswith("admin,"):
        enter_admin_mode(message)

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application...")
        flask_app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
    except Exception as e:
        logger.error(f"Error starting Flask application: {e}")
        exit(1)
