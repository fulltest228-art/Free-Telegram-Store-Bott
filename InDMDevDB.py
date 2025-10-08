import sqlite3
from datetime import datetime
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_FILE = 'InDMDevDBShop.db'
db_connection = sqlite3.connect(DB_FILE, check_same_thread=False)
db_connection.row_factory = sqlite3.Row
cursor = db_connection.cursor()
db_lock = threading.Lock()

class CreateTables:
    @staticmethod
    def create_all_tables():
        try:
            with db_lock:
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopUserTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    wallet INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopAdminTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    wallet INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopProductTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    productnumber INTEGER UNIQUE NOT NULL DEFAULT (ABS(RANDOM()) % 1000000),
                    admin_id INTEGER NOT NULL,
                    username TEXT,
                    productname TEXT NOT NULL,
                    productdescription TEXT,
                    productprice INTEGER DEFAULT 0,
                    productimagelink TEXT,
                    productdownloadlink TEXT,
                    productkeysfile TEXT,
                    productquantity INTEGER DEFAULT 0,
                    productcategory TEXT DEFAULT 'Default Category',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES ShopAdminTable(admin_id)
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopOrderTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    buyerid INTEGER NOT NULL,
                    buyerusername TEXT,
                    productname TEXT NOT NULL,
                    productprice TEXT NOT NULL,
                    orderdate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paidmethod TEXT DEFAULT 'NO',
                    productdownloadlink TEXT,
                    productkeys TEXT,
                    buyercomment TEXT,
                    ordernumber INTEGER UNIQUE NOT NULL,
                    productnumber INTEGER NOT NULL,
                    payment_id TEXT,
                    FOREIGN KEY (buyerid) REFERENCES ShopUserTable(user_id),
                    FOREIGN KEY (productnumber) REFERENCES ShopProductTable(productnumber)
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopCategoryTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    categorynumber INTEGER UNIQUE NOT NULL,
                    categoryname TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS PaymentMethodTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    username TEXT,
                    method_name TEXT UNIQUE NOT NULL,
                    token_keys_clientid TEXT,
                    secret_keys TEXT,
                    activated TEXT DEFAULT 'NO',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                db_connection.commit()
                logger.info("All database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            db_connection.rollback()
            raise

CreateTables.create_all_tables()

class CreateDatas:
    @staticmethod
    def add_user(user_id, username):
        try:
            with db_lock:
                cursor.execute(
                    "INSERT OR IGNORE INTO ShopUserTable (user_id, username, wallet) VALUES (?, ?, ?)",
                    (user_id, username, 0)
                )
                db_connection.commit()
                logger.info(f"User added: {username} (ID: {user_id})")
                return True
        except Exception as e:
            logger.error(f"Error adding user {username}: {e}")
            db_connection.rollback()
            return False

    @staticmethod
    def add_admin(admin_id, username):
        try:
            with db_lock:
                cursor.execute(
                    "INSERT OR IGNORE INTO ShopAdminTable (admin_id, username, wallet) VALUES (?, ?, ?)",
                    (admin_id, username, 0)
                )
                db_connection.commit()
                logger.info(f"Admin added: {username} (ID: {admin_id})")
                return True
        except Exception as e:
            logger.error(f"Error adding admin {username}: {e}")
            db_connection.rollback()
            return False

    @staticmethod
    def add_product(admin_id, username, productname, productdescription, productprice, productquantity, productcategory, productimagelink=None):
        try:
            with db_lock:
                cursor.execute(
                    "INSERT INTO ShopProductTable (admin_id, username, productname, productdescription, productprice, productquantity, productcategory, productimagelink) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (admin_id, username, productname, productdescription, productprice, productquantity, productcategory, productimagelink)
                )
                db_connection.commit()
                logger.info(f"Product added: {productname}")
                return True
        except Exception as e:
            logger.error(f"Error adding product {productname}: {e}")
            db_connection.rollback()
            return False

class GetDataFromDB:
    @staticmethod
    def get_user(user_id):
        try:
            with db_lock:
                cursor.execute("SELECT * FROM ShopUserTable WHERE user_id = ?", (user_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    @staticmethod
    def get_products():
        try:
            with db_lock:
                cursor.execute("SELECT * FROM ShopProductTable")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return None

    @staticmethod
    def get_product_by_id(productnumber):
        try:
            with db_lock:
                cursor.execute("SELECT * FROM ShopProductTable WHERE productnumber = ?", (productnumber,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting product {productnumber}: {e}")
            return None

    @staticmethod
    def get_categories():
        try:
            with db_lock:
                cursor.execute("SELECT DISTINCT productcategory FROM ShopProductTable")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return None

class UpdateData:
    @staticmethod
    def update_product_quantity(productnumber, new_quantity):
        try:
            with db_lock:
                cursor.execute("UPDATE ShopProductTable SET productquantity = ? WHERE productnumber = ?", (new_quantity, productnumber))
                db_connection.commit()
                logger.info(f"Updated quantity for product {productnumber}")
                return True
        except Exception as e:
            logger.error(f"Error updating quantity for product {productnumber}: {e}")
            db_connection.rollback()
            return False
