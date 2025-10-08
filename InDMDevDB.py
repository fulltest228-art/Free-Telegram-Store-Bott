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
db_connection.row_factory = sqlite3.Row  # Enable dict-like access to rows
cursor = db_connection.cursor()
db_lock = threading.Lock()

class CreateTables:
    @staticmethod
    def create_all_tables():
        try:
            with db_lock:
                # Create ShopUserTable
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopUserTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    wallet INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                # Create ShopAdminTable
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopAdminTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    wallet INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                # Create ShopProductTable
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopProductTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    productnumber INTEGER UNIQUE NOT NULL,
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
                # Create ShopOrderTable
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
                # Create ShopCategoryTable
                cursor.execute("""CREATE TABLE IF NOT EXISTS ShopCategoryTable(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    categorynumber INTEGER UNIQUE NOT NULL,
                    categoryname TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                # Create PaymentMethodTable
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
    # [Add other CreateDatas methods as needed from original]

class GetDataFromDB:
    @staticmethod
    def GetPaymentMethodTokenKeysCleintID(method_name):
        try:
            cursor.execute(f"SELECT DISTINCT token_keys_clientid FROM PaymentMethodTable WHERE method_name = '{method_name}'")
            payment_method = cursor.fetchone()[0]
            return payment_method if payment_method is not None else None
        except Exception as e:
            print(e)
            return None
    @staticmethod
    def GetPaymentMethodSecretKeys(method_name):
        try:
            cursor.execute(f"SELECT DISTINCT secret_keys FROM PaymentMethodTable WHERE method_name = '{method_name}'")
            payment_method = cursor.fetchone()[0]
            return payment_method if payment_method is not None else None
        except Exception as e:
            print(e)
            return None
    @staticmethod
    def GetAllPaymentMethodsInDB():
        try:
            cursor.execute(f"SELECT DISTINCT method_name FROM PaymentMethodTable")
            payment_methods = cursor.fetchall()
            return payment_methods if payment_methods else None
        except Exception as e:
            print(e)
            return None
    # [Add other GetDataFromDB methods like GetProductCategories, GetProductIDs, etc., replacing 'connected' with 'cursor']

class CleanData:
    def CleanShopUserTable():
        try:
            cursor.execute("DELETE FROM ShopUserTable")
            db_connection.commit()
        except Exception as e:
            print(e)
    # [Add other CleanData methods as in original, replacing 'connected' with 'cursor']
