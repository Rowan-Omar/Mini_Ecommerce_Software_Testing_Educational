import random
import time
import requests
import os
import socket
from dotenv import load_dotenv
from db_operations import (
    get_user_by_credentials, get_seller_status, get_product_details, update_product_stock,
    insert_product, finalize_order, get_all_products
)

load_dotenv()

# --- Global In-Memory Session Data ---
# These variables track the current session and cart status.
CURRENT_USER = {"id": None, "role": None}
CART = {} # {product_id (int): quantity (int)}

# =================================================================
# UTILITIES
# =================================================================

def square_api_integration(total_amount, nonce="cnon:card-nonce-ok"):
    """
    Square API Integration with proper handling of DECLINED payments.
    """
    SQUARE_API_URL = "https://connect.squareupsandbox.com/v2/payments"
    SQUARE_ACCESS_TOKEN = "EAAAl3PMyhTGg7_s8mFSUWHEdam4bND16lE8aYfMnvtKJy97j4DJhwiXvJvnqYgk" #os.getenv("SQUARE_ACCESS_TOKEN")

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = random.randint(10000, 99999)

    payload = {
        "source_id": nonce,
        "amount_money": {
            "amount": int(total_amount * 100),
            "currency": "USD"
        },
        "idempotency_key": f"order-{local_ip}-{random.randint(10000, 99999)}"
    }

    try:
        response = requests.post(
            SQUARE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        data = response.json()

        # ✅ CASE 1: Payment object exists
        if "payment" in data:
            payment = data["payment"]

            if payment.get("status") == "COMPLETED":
                return {
                    "status": "success",
                    "message": "Transaction authorized and captured.",
                    "id": payment["id"]
                }

            elif payment.get("status") == "FAILED":
                # Look inside for decline reason
                error_msg = None
                if "errors" in payment.get("card_details", {}):
                    error_msg = payment["card_details"]["errors"][0].get("detail")
                elif "errors" in data:
                    error_msg = data["errors"][0].get("detail")

                return {
                    "status": "declined",
                    "message": f"Payment declined: {error_msg or 'Unknown reason'}",
                    "id": payment["id"]
                }

            else:
                return {
                    "status": "pending",
                    "message": f"Payment status: {payment.get('status')}",
                    "id": payment["id"]
                }

        # ✅ CASE 2: Top-level error (e.g., bad request, invalid nonce, etc.)
        elif "errors" in data:
            return {
                "status": "failure",
                "message": f"Square API Error: {data['errors'][0].get('detail')}",
                "id": None
            }

        # ✅ CASE 3: Totally unexpected response
        else:
            return {
                "status": "failure",
                "message": "Unknown Square API response.",
                "id": None
            }

    except requests.exceptions.RequestException as e:
        return {
            "status": "failure",
            "message": f"Network/API error: {e}",
            "id": None
        }

    
def simulate_payment_api(amount):
    """
    FR-B4 Simulation: Simulates a payment API call.
    Forces failure if amount > 500 (Alternative Flow testing).
    """
    if amount > 500:
        return {"status": "failed", "message": "Transaction declined: High value risk (>$500)."}
    
    time.sleep(0.01)
    
    if random.random() < 0.95:
         return {"status": "success", "message": f"Payment confirmed. Ref: {random.randint(10000, 99999)}"}
    else:
        # Alternative Flow 5a
        return {"status": "failed", "message": "System timeout."}

# =================================================================
# AUTHENTICATION & SESSION MANAGEMENT
# =================================================================

def api_login_user(email, password):
    """
    Performs login and updates the CURRENT_USER session state.
    Returns: success status and message.
    """
    user = get_user_by_credentials(email, password)
    
    if not user:
        return {"status": "error", "message": "**Invalid email or password.**"}
    
    user_id = user['user_id']
    role = user['role']
    
    if role == 'seller':
        status_row = get_seller_status(user_id)
        if status_row and status_row['status'] == 'approved':
            CURRENT_USER["id"] = user_id
            CURRENT_USER["role"] = role
            return {"status": "success", "role": "seller", "message": f"Welcome back, approved seller: {user_id}"}
        elif status_row and status_row['status'] == 'pending':
            return {"status": "error", "message": "Seller account is registered but still **pending admin approval**."}
        else:
            return {"status": "error", "message": "Seller account is invalid or unapproved."}
            
    elif role == 'buyer':
        CURRENT_USER["id"] = user_id
        CURRENT_USER["role"] = role
        return {"status": "success", "role": "buyer", "message": f"Welcome back, buyer: {user_id}"}
        
    else:
         return {"status": "error", "message": "Account role is unsupported."}

def api_logout_user():
    """Clears the session state."""
    CURRENT_USER["id"] = None
    CURRENT_USER["role"] = None
    CART.clear()

# =================================================================
# SELLER FUNCTIONS (UC-01: Add Product)
# =================================================================

def api_add_product(name, description, price, stock, image_format, image_size_mb):
    """
    Simulates FR-S2 and UC-01. Inserts a product after validation.
    """
    seller_id = CURRENT_USER.get("id")
    if not seller_id or CURRENT_USER.get("role") != 'seller':
        return {"status": "error", "message": "Precondition failed: Not logged in as a seller."}

    # Precondition Check (UC-01) - Checked during login, but good to double-check
    status_row = get_seller_status(seller_id)
    if not status_row or status_row['status'] != 'approved':
        return {"status": "error", "message": "Precondition failed: Seller is not approved."}

    # --- Input Validation ---
    if not name or price is None or stock is None:
        # Alternative Flow 2a
        return {"status": "error", "message": "Validation failed: Name, price, stock are required."}
    
    if price <= 0:
        return {"status": "error", "message": "Validation failed: Price must be a positive number."}
    if stock < 0:
        return {"status": "error", "message": "Validation failed: Stock must be a non-negative integer."}
        
    valid_formats = ["PNG", "JPG", "JPEG"]
    if image_format.upper() not in valid_formats:
        # Alternative Flow 3a
        return {"status": "error", "message": "Validation failed: Only PNG/JPG/JPEG formats allowed."}

    # Image Size Constraint (from SRS)
    if image_size_mb > 5:
        return {"status": "error", "message": "Validation failed: Image size must be under 5MB."}

    # --- Main Flow ---
    try:
        product_id = insert_product(seller_id, name, description, price, stock, image_format)
        return {"status": "success", "message": f"Product '{name}' added successfully with ID {product_id}."}
    except Exception as e:
        return {"status": "fatal_error", "message": f"Database error during insert: {e}"}

# =================================================================
# BUYER FUNCTIONS (FR-B2, UC-02)
# =================================================================

def api_add_to_cart(product_id, quantity=1):
    """
    Simulates FR-B2. Adds a product to the in-memory CART.
    """
    product = get_product_details(product_id)
    
    if not product:
        return {"status": "error", "message": f"Product ID {product_id} not found."}
    
    if quantity <= 0:
        return {"status": "error", "message": "Quantity must be positive."}

    current_cart_qty = CART.get(product_id, 0)
    
    if product["stock"] < (current_cart_qty + quantity):
        return {"status": "error", "message": f"Insufficient stock. Available: {product['stock']}. Already in cart: {current_cart_qty}."}

    CART[product_id] = current_cart_qty + quantity
    return {"status": "success", "message": f"{quantity} of {product['name']} added to cart."}

def api_checkout(card_number, cvc):
    """
    Handles the full checkout process (UC-02 / FR-B4).
    Now routes the payment based on the selected method.
    """
    global CART

    if not CURRENT_USER or CURRENT_USER.get('role') != 'buyer':
        return {"status": "error", "message": "Checkout requires a logged-in buyer."}
    
    if not CART:
        return {"status": "error", "message": "Cart is empty. Nothing to checkout."}
        
    # 1. Calculate Total Amount
    total_amount = 0
    items_to_process = {}
    
    for p_id, qty in CART.items():
        product = get_product_details(p_id)
        if product:
            total_amount += product["price"] * qty
            items_to_process[p_id] = {"qty": qty, "product": product}
        else:
            print(f"WARNING: Product ID {p_id} in cart not found in DB.")
            
    if total_amount <= 0:
        return {"status": "error", "message": "Cannot checkout, total amount is zero."}

    if card_number == "4111111111111111" and cvc == "123":
        test_nonce = "cnon:card-nonce-ok"
    elif card_number ==  "4000000000000002" and cvc == "123":
        test_nonce = "cnon:card-nonce-declined"
    
    # 2. Process Payment based on selection
    payment_result = square_api_integration(total_amount, nonce=test_nonce) 


    if payment_result["status"] != "success":
        # Payment fails (Alternative Flow 5a)
        return {"status": "error", "message": f"Payment failed: {payment_result['message']}"}

    # 3. Fulfillment (Postcondition: Stock update)
    
    # Store order here (Simulation: Order is stored, status 'Pending')
    order_id = payment_result['id']
    print(f"ORDER SUCCESS: Order {order_id} placed for user {CURRENT_USER['id']}")

    # Update Stock (FR-S3)
    for p_id, data in items_to_process.items():
        update_product_stock(p_id, -data["qty"])
        
    # Clear cart
    CART = {}

    return {"status": "success", "message": f"Order #{order_id} placed. Stock updated."}
