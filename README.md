# 🛍️ Mini Fashion E-commerce Test Execution Plan

This document serves as the **Test Execution Checklist** for the **Mini Fashion E-commerce Simulator**. Use this plan to apply software testing concepts, execute test cases, and document the system's behavior.

---

## 🚀 1. Setup & Pre-requisites

### 1.1 Technical Requirements

This section defines the mandatory environment setup and tools required before starting test execution.

| Component | Requirement | Details |
| :--- | :--- | :--- |
| **Operating System** | **Windows 10 or 11** | The application is a desktop GUI app built specifically for the Windows OS. |
| **Runtime** | **Python 3.9+** | The standard Python environment is required to execute the scripts. |
| **Dependencies** | **Standard Library Only** | The application uses built-in Python modules (like `tkinter`, `sqlite3`). The `requirements.txt` file contains other required packages. Open a terminal in your project’s root folder (where requirements.txt is located). Then run, ```pip install -r requirements.txt```|

### 1.2 Execution Setup

1.  Ensure the three Python files (`main.py`, `system_logic.py`, and `db_operations.py`) are in the same directory.

2.  Run the application from your terminal. Since `main.py` is the main file, use:
    ```bash    
        python main.py
    ```

### 1.3 Mock Test Data Overview

| Category | Item | Value / Note | Purpose in Testing | 
| :--- | :--- | :--- | :--- | 
| **User Role** | Buyer | `buyer@example.com` / `passw123` | Main flow access. | 
| **User Role** | Approved Seller | `seller@approved.com` / `passw123` | Testing **UC-01 (Add Product)**. | 
| **User Role** | Pending Seller | `seller@pending.com` / `passw123` | Testing **Alt Flow (FR-A1)**. | 
| **Product Data** | T-shirt (ID 1) | Price $19.99, Stock **50** | Main purchase flow. | 
| **Product Data** | Sneaker (ID 2) | Price $149.00, Stock **1** | Testing **Stock Boundary**. | 
| **Payment Success** | Mock Square Card | `4111111111111111` / `123` | Guaranteed success for testing stock decrement. | 
| **Payment Failure** | Mock Square Card | `4000000000000002` / `123` | Guaranteed failure for testing error messages (UC-02 Alt Flow). | 

---

## 📝 2. Student Notes

The goal of this exercise is to execute test cases, document the **Actual Result**, and determine the **Status** (Pass/Fail) to identify any defects in the provided code. Then generate the appropriate reports and deliver them through GitHub (create folder for you inside `reports` directory)
