import tkinter as tk
from tkinter import messagebox
from functools import partial
import os
from tkinter import filedialog

# Import modules
from db_operations import initialize_db, get_all_products, get_product_details
from system_logic import (
    CART, CURRENT_USER, api_login_user, api_logout_user, 
    api_add_to_cart, api_checkout, api_add_product
)

# --- Tkinter GUI Setup ---
ROOT = tk.Tk()
ROOT.title("Mini Fashion E-commerce")
ROOT.geometry("800x600")

# --- Frames (Containers for different views) ---
login_frame = tk.Frame(ROOT)
buyer_frame = tk.Frame(ROOT)
cart_frame = tk.Frame(ROOT)
seller_frame = tk.Frame(ROOT)

def show_frame(frame):
    """Hides all frames and shows the selected frame."""
    for f in [login_frame, buyer_frame, cart_frame, seller_frame]:
        f.pack_forget()
    frame.pack(fill='both', expand=True)

def handle_logout():
    """Handles session cleanup and returns to login screen."""
    api_logout_user()
    messagebox.showinfo("Logout", "You have been logged out.")
    setup_login_frame()
    show_frame(login_frame)

# =================================================================
# 1. Login View
# =================================================================

def login_user(email_entry, password_entry):
    """Handles the email/password login and redirects based on role."""
    email = email_entry.get().strip()
    password = password_entry.get()
    
    if not email:
        messagebox.showerror("Login Error", "Email field cannot be empty.")
        return
    if not password:
        messagebox.showerror("Login Error", "Password field cannot be empty.")
        return

    result = api_login_user(email, password)
    
    if result["status"] == "success":
        messagebox.showinfo("Login Success", result["message"])
        if result["role"] == "buyer":
            refresh_buyer_view()
            show_frame(buyer_frame)
        elif result["role"] == "seller":
            setup_seller_frame() # Re-setup to show correct Seller ID
            show_frame(seller_frame)
    else:
        messagebox.showerror("Login Error", result["message"])

def setup_login_frame():
    """Sets up the widgets for the login view."""
    for widget in login_frame.winfo_children():
        widget.destroy()
        
    tk.Label(login_frame, text="E-commerce System Login", font=('Arial', 18, 'bold')).pack(pady=20)
    # tk.Label(login_frame, text="Use 'buyer@example.com' or 'seller@approved.com' / passw123").pack(pady=5, fg='gray')
    
    tk.Label(login_frame, text="Email:").pack(pady=5)
    email_entry = tk.Entry(login_frame, width=30)
    email_entry.pack(pady=5)
    
    tk.Label(login_frame, text="Password:").pack(pady=5)
    password_entry = tk.Entry(login_frame, width=30, show='*')
    password_entry.pack(pady=5)
    
    tk.Button(login_frame, text="Login", 
              command=lambda: login_user(email_entry, password_entry), 
              bg="#4CAF50", fg="white", padx=10, pady=5).pack(pady=15)

# =================================================================
# 2. Buyer View (Catalog)
# =================================================================

# Frame for the product list (scrollable container)
product_list_container = tk.Frame(buyer_frame)
product_list_container.pack(fill='both', expand=True, padx=10, pady=10)

def refresh_buyer_view():
    """Fetches products and updates the buyer interface."""
    
    # Clear previous contents of the container
    for widget in product_list_container.winfo_children():
        widget.destroy()

    tk.Label(product_list_container, text="Product Catalog", font=('Arial', 16, 'bold')).pack(pady=10)
    
    cart_info = f"Cart Items: {sum(CART.values())} | "
    cart_info += "Logged in as Buyer ID " + str(CURRENT_USER.get('id', 'N/A'))
    
    tk.Label(product_list_container, text=cart_info, fg='blue').pack()
    
    button_frame = tk.Frame(product_list_container)
    button_frame.pack(pady=5)

    tk.Button(button_frame, text=f"View Cart ({sum(CART.values())})", 
              command=refresh_cart_view, bg="#FFC107", padx=10, pady=5).pack(side='left', padx=10)
    # tk.Button(button_frame, text="Logout", 
    #           command=handle_logout).pack(side='left', padx=10)
    
    # Product Grid Header
    header_frame = tk.Frame(product_list_container, relief=tk.RIDGE, bd=2)
    header_frame.pack(fill='x', pady=5)
    tk.Label(header_frame, text="Name", font=('Arial', 10, 'bold'), width=20, anchor='w').pack(side='left', padx=5)
    tk.Label(header_frame, text="Price", font=('Arial', 10, 'bold'), width=10).pack(side='left', padx=5)
    tk.Label(header_frame, text="Stock", font=('Arial', 10, 'bold'), width=8).pack(side='left', padx=5)
    tk.Label(header_frame, text="Action", font=('Arial', 10, 'bold'), width=15).pack(side='left', padx=5)

    products = get_all_products()
    
    for product in products:
        p_id = product["id"]
        product_frame = tk.Frame(product_list_container, bd=1, relief=tk.GROOVE)
        product_frame.pack(fill='x', pady=2)
        
        tk.Label(product_frame, text=product["name"], width=25, anchor='w').pack(side='left', padx=5)
        tk.Label(product_frame, text=f"${product['price']:.2f}", width=10).pack(side='left', padx=5)
        tk.Label(product_frame, text=product["stock"], width=10).pack(side='left', padx=5)
        
        btn_add = tk.Button(product_frame, text="Add to Cart", 
                            command=partial(handle_add_to_cart, p_id),
                            bg="#2196F3", fg="white")
        btn_add.pack(side='left', padx=5)

def handle_add_to_cart(product_id):
    """Wrapper to handle GUI response after adding to cart."""
    result = api_add_to_cart(product_id, 1) # Always add 1 for simplicity
    
    if result["status"] == "success":
        messagebox.showinfo("Success", result["message"])
    else:
        messagebox.showerror("Error", result["message"])
        
    refresh_buyer_view() # Update cart count and stock

# =================================================================
# 3. Cart View
# =================================================================

def refresh_cart_view():
    """Updates and shows the cart and checkout interface."""
    show_frame(cart_frame)
    
    for widget in cart_frame.winfo_children():
        widget.destroy()
        
    tk.Label(cart_frame, text="Shopping Cart", font=('Arial', 18, 'bold')).pack(pady=20)
    
    if not CART:
        tk.Label(cart_frame, text="Your cart is empty.", fg='red').pack(pady=20)
        tk.Button(cart_frame, text="Back to Browsing", command=lambda: show_frame(buyer_frame)).pack()
        return

    # Cart List Header
    header_frame = tk.Frame(cart_frame)
    header_frame.pack(fill='x', pady=5, padx=20)
    tk.Label(header_frame, text="Product ID", font=('Arial', 10, 'bold'), width=10).pack(side='left', padx=5)
    tk.Label(header_frame, text="Name", font=('Arial', 10, 'bold'), width=20, anchor='w').pack(side='left', padx=5)
    tk.Label(header_frame, text="Price", font=('Arial', 10, 'bold'), width=10).pack(side='left', padx=5)
    tk.Label(header_frame, text="Qty", font=('Arial', 10, 'bold'), width=5).pack(side='left', padx=5)
    tk.Label(header_frame, text="Subtotal", font=('Arial', 10, 'bold'), width=10).pack(side='left', padx=5)
    
    total_amount = 0
    
    for p_id, qty in CART.items():
        product = get_product_details(p_id)
        
        if product:
            price = product["price"]
            subtotal = price * qty
            total_amount += subtotal
            
            item_frame = tk.Frame(cart_frame, bd=1, relief=tk.GROOVE)
            item_frame.pack(fill='x', pady=2, padx=20)
            
            tk.Label(item_frame, text=p_id, width=10).pack(side='left', padx=5)
            tk.Label(item_frame, text=product["name"], width=25, anchor='w').pack(side='left', padx=5)
            tk.Label(item_frame, text=f"${price:.2f}", width=10).pack(side='left', padx=5)
            tk.Label(item_frame, text=qty, width=5).pack(side='left', padx=5)
            tk.Label(item_frame, text=f"${subtotal:.2f}", width=10).pack(side='left', padx=5)
            

    tk.Label(cart_frame, text="---", font=('Arial', 12, 'bold')).pack(pady=10)
    tk.Label(cart_frame, text=f"Total Payable: ${total_amount:.2f}", font=('Arial', 14, 'bold'), fg='darkgreen').pack(pady=5)

    # --- Card Details Input ---
    card_details_frame = tk.Frame(cart_frame)
    card_details_frame.pack(pady=10)

    tk.Label(card_details_frame, text="Card Number:").pack(side='left', padx=5)
    card_entry = tk.Entry(card_details_frame, width=20)
    # card_entry.insert(0, "4111111111110000") # Default to Success card
    card_entry.pack(side='left', padx=5)
    
    tk.Label(card_details_frame, text="CVC:").pack(side='left', padx=5)
    cvc_entry = tk.Entry(card_details_frame, width=5, show='*')
    # cvc_entry.insert(0, "123")
    cvc_entry.pack(side='left', padx=5)
    
    # Test credentials instruction
    # tk.Label(cart_frame, text="Use 4111...0000 for SUCCESS or 4111...4040 for DENIAL.", fg='gray', font=('Arial', 8)).pack()
    
    # --- Checkout Button (Updated Command) ---
    tk.Button(cart_frame, text="Complete Checkout", 
              # Now pass card_entry and cvc_entry values
              command=lambda: handle_checkout(
                  
                  card_entry.get(),
                  cvc_entry.get()
              ), 
              bg="#4CAF50", fg="white", padx=15, pady=8).pack(pady=15)
              
    tk.Button(cart_frame, text="Back to Browsing", command=lambda: show_frame(buyer_frame)).pack()

def handle_checkout(card_number, cvc):
    """
    Wrapper to handle GUI response after checkout.
    Accepts the selected payment method and card details.
    """
    
    # We now call api_checkout with the new arguments
    result = api_checkout( card_number, cvc) 
    
    if result["status"] == "success":
        messagebox.showinfo("Order Success", f"{result['message']}")
        refresh_buyer_view() # Clears cart and updates stock view
        show_frame(buyer_frame)
    else:
        # Show specific error message from the API simulation
        messagebox.showerror("Order Failed", result["message"])
        refresh_cart_view() # Reload cart to reflect current state or error

# =================================================================
# 4. Seller View
# =================================================================

def setup_seller_frame():
    """Sets up the seller dashboard for UC-01 Add Product."""
    for widget in seller_frame.winfo_children():
        widget.destroy()
        
    tk.Label(seller_frame, text="Seller Dashboard", font=('Arial', 18, 'bold')).pack(pady=20)
    tk.Label(seller_frame, text=f"Logged in as Seller ID: {CURRENT_USER.get('id', 'N/A')}", fg='blue').pack()
    
    tk.Label(seller_frame, text="Name").pack()
    name_entry = tk.Entry(seller_frame)
    name_entry.pack()

    tk.Label(seller_frame, text="Price (>0)").pack()
    price_entry = tk.Entry(seller_frame)
    price_entry.insert(0, "50.00")
    price_entry.pack()

    tk.Label(seller_frame, text="Stock (>=0)").pack()
    stock_entry = tk.Entry(seller_frame)
    stock_entry.insert(0, "10")
    stock_entry.pack()

    tk.Label(seller_frame, text="Upload Product Image (JPG/PNG, ≤ 5MB)").pack()
    image_path_var = tk.StringVar()

    def select_image():
        filepath = filedialog.askopenfilename(
            title="Select Product Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
        )
        if filepath:
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            ext = os.path.splitext(filepath)[1].lower()
            
            if ext not in [".jpg", ".jpeg", ".png"]:
                messagebox.showerror("Invalid Format", "Only JPG or PNG images are allowed.")
                return
            if size_mb > 5:
                messagebox.showerror("File Too Large", "Image must not exceed 5MB.")
                return
            
            image_path_var.set(filepath)
            messagebox.showinfo("Image Selected", f"File selected: {os.path.basename(filepath)}")

    tk.Button(seller_frame, text="Select Image", command=select_image, bg="#607D8B", fg="white").pack(pady=5)

    def do_add_product():
        """Handles input validation and calls the API function."""
        try:
            name = name_entry.get()
            price = float(price_entry.get()) 
            stock = int(stock_entry.get())
            image_path = image_path_var.get()
            
            if not image_path:
                messagebox.showerror("Missing Image", "Please select an image for the product.")
                return
            
            size_mb = os.path.getsize(image_path) / (1024 * 1024)
            ext = os.path.splitext(image_path)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png"]:
                messagebox.showerror("Invalid Format", "Only JPG or PNG images are allowed.")
                return
            if size_mb > 5:
                messagebox.showerror("File Too Large", "Image must not exceed 5MB.")
                return
            
            result = api_add_product(name, "GUI-Added Product", price, stock, ext.upper(), round(size_mb, 2))
            
            if result["status"] == "success":
                messagebox.showinfo("Success", result["message"])
                # Clear fields after success
                name_entry.delete(0, tk.END)
                price_entry.delete(0, tk.END)
                price_entry.insert(0, "50.00")
                stock_entry.delete(0, tk.END)
                stock_entry.insert(0, "10")
                image_path_var.set("")
            else:
                messagebox.showerror("Failure", result["message"])
                
        except ValueError:
            messagebox.showerror("Input Error", "Price must be a decimal number and Stock must be a whole integer.")

    tk.Button(seller_frame, text="Add Product", command=do_add_product,
              bg="#FF9800", fg="white", padx=10, pady=5).pack(pady=15)
    

# =================================================================
# MAIN EXECUTION
# =================================================================

def main():
    """Initializes the DB and starts the GUI."""
    initialize_db()
    
    # Setup initial view
    setup_login_frame()
    show_frame(login_frame)
    
    ROOT.mainloop()

if __name__ == "__main__":
    main()
