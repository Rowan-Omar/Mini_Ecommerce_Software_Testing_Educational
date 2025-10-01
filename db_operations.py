import sqlite3
import os

DB_NAME = "ecommerce_test_db.sqlite"

def get_db_connection():
    """Returns a connection object for the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by column name
    return conn

def initialize_db():
    """
    Initializes the database tables (users, sellers, products, orders) and 
    seeds initial data if they don't exist.
    """
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users Table (for email/password login)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL -- 'buyer', 'seller'
        );
    """)

    # 2. Sellers Table (For approval status - UC-01 Precondition)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL -- 'approved' or 'pending'
        );
    """)

    # 3. Products Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            seller_id TEXT,
            image_format TEXT,
            FOREIGN KEY(seller_id) REFERENCES sellers(id)
        );
    """)

    # 4. Orders Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            buyer_id TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL,
            payment_ref TEXT
        );
    """)

    # --- Seed Initial Data ---
    if cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        # Test Accounts: Password is 'passw123' for all
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", 
                       ("B007", "buyer@example.com", "passw123", "buyer"))
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", 
                       ("S999", "seller@approved.com", "passw123", "seller"))
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", 
                       ("S001", "seller@pending.com", "passw123", "seller"))

    if cursor.execute("SELECT COUNT(*) FROM sellers").fetchone()[0] == 0:
        cursor.execute("INSERT INTO sellers VALUES (?, ?, ?)", ("S999", "Approved Seller", "approved"))
        cursor.execute("INSERT INTO sellers VALUES (?, ?, ?)", ("S001", "Pending Seller", "pending"))
    
    if cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        cursor.execute("INSERT INTO products (name, price, stock, seller_id) VALUES (?, ?, ?, ?)", 
                       ("Blue Denim", 49.99, 10, "S999"))
        cursor.execute("INSERT INTO products (name, price, stock, seller_id) VALUES (?, ?, ?, ?)", 
                       ("Cotton Tee", 19.50, 50, "S999"))
        cursor.execute("INSERT INTO products (name, price, stock, seller_id) VALUES (?, ?, ?, ?)", 
                       ("Leather Jacket", 199.99, 5, "S999"))

    conn.commit()
    conn.close()
    print("Database initialized with sample data.")

def get_user_by_credentials(email, password):
    """Retrieves user details based on email and password."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, role, password_hash FROM users WHERE email = ? AND password_hash = ?", 
                   (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def get_seller_status(seller_id):
    """Retrieves the approval status of a seller."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM sellers WHERE id = ?", (seller_id,))
    status = cursor.fetchone()
    conn.close()
    return status

def get_all_products():
    """Retrieves all products with stock > 0."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM products WHERE stock > 0 ORDER BY id DESC")
    products = cursor.fetchall()
    conn.close()
    return products

def get_product_details(product_id):
    """Retrieves details for a single product."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, stock, price FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def insert_product(seller_id, name, description, price, stock, image_format):
    """Inserts a new product into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (name, description, price, stock, seller_id, image_format) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, description, round(price, 2), stock, seller_id, image_format.upper()))
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id

def update_product_stock(product_id, quantity_change):
    """Updates the stock of a product (positive for adding, negative for subtracting)."""
    product = get_product_details(product_id)
    if product:
        new_stock = product["stock"] + quantity_change
        final_stock = max(0, new_stock)

        # Update the DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (final_stock, product_id))
        conn.commit()
        conn.close()

        return True
    return False


def finalize_order(buyer_id, total_amount, payment_ref, order_items):
    """
    Inserts a new order and updates product stock in a single transaction.
    Returns the new order ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Insert Order
        cursor.execute("""
            INSERT INTO orders (buyer_id, total, status, payment_ref) 
            VALUES (?, ?, ?, ?)
        """, (buyer_id, round(total_amount, 2), "Pending", payment_ref))
        order_id = cursor.lastrowid
        
        # 2. Update Stock for each item
        for item in order_items:
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", 
                           (item["quantity"], item["product_id"]))
            
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
