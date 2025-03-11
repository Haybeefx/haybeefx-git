import sqlite3
import hashlib
import random
import re
import time
from getpass import getpass

connect = sqlite3.connect("customers.db")

connect.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    account_number TEXT UNIQUE NOT NULL,
    balance REAL DEFAULT 0.0
)
""")

connect.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL NOT NULL,
    sender_account TEXT DEFAULT NULL,
    recipient_account TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

def generate_account_number():
    while True:
        account_number = str(random.randint(1000000000, 9999999999))
        existing = connect.execute("SELECT 1 FROM users WHERE account_number = ?", (account_number,)).fetchone()
        if not existing:
            return account_number

def validate_password(password):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    return re.match(pattern, password)

def sign_up():
    print("*************** Sign Up ***************")
    while True:
        full_name = input("Enter your first and last name: ").strip()
        if not full_name:
            print("Full name cannot be blank.")
            continue
        break
    
    while True:
        username = input("Enter your username: ").strip()
        if not username:
            print("Username cannot be blank.")
            continue
        break
    
    while True:
        password = getpass("Enter your password: ").strip()
        if not validate_password(password):
            print("Password must be at least 8 characters long, with an uppercase, lowercase, number, and special character.")
            continue
        confirm_password = getpass("Confirm your password: ").strip()
        if password != confirm_password:
            print("Passwords don't match. Try again.")
            continue
        break
    
    while True:
        try:
            initial_deposit = float(input("Enter an initial deposit (minimum 2000): "))
            if initial_deposit < 2000:
                print("Minimum deposit is 2000.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a numeric value.")
    
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    account_number = generate_account_number()
    
    try:
        connect.execute("INSERT INTO users (full_name, username, password, account_number, balance) VALUES (?, ?, ?, ?, ?)",
                       (full_name, username, hashed_password, account_number, initial_deposit))
        connect.commit()
        print(f"\nSign Up successful! Your account number is: {account_number}.")
        time.sleep(2)
        log_in()
    except sqlite3.IntegrityError:
        print("Username already exists. Try again.")

def log_in():
    print("*************** Log In ***************")
    while True:
        username = input("Enter your username: ").strip()
        password = getpass("Enter your password: ").strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = connect.execute("SELECT id, full_name FROM users WHERE username = ? AND password = ?", 
                              (username, hashed_password)).fetchone()
        if user:
            print(f"Welcome, {user[1]}!\n")
            time.sleep(1)
            banking_menu(user[0])
        else:
            print("Invalid username or password. Try again.")

def banking_menu(user_id):
    while True:
        print("""
************** Banking Menu **************
1. Check Balance
2. Deposit
3. Withdraw
4. Transfer
5. Transaction History
6. Log Out
""")
        action = input("Choose an option: ").strip()
        if action == "1":
            print(check_balance(user_id))
        elif action == "2":
            deposit(user_id)
        elif action == "3":
            withdraw(user_id)
        elif action == "4":
            transfer(user_id)
        elif action == "5":
            transaction_history(user_id)
        elif action == "6":
            print("Log out successful...\n")
            time.sleep(1)
            break
        else:
            print("Invalid choice. Try again.")
    main_menu()

def check_balance(user_id):
    balance = connect.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    return f"Your balance: ₦{balance:.2f}"

def deposit(user_id):
    while True:
        try:
            amount = float(input("Enter deposit amount: "))

            if amount <= 0:
                print("Deposit must be greater than 0. Please enter a valid amount.")
            else:
                connect.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
                connect.execute("INSERT INTO transactions (user_id, amount) VALUES (?, ?)", (user_id, amount))
                connect.commit()
                print("Deposit successful!")
                time.sleep(1)
                return
        except ValueError:
            print("Invalid input. Please enter a numeric amount.")


def withdraw(user_id):
    while True:
        try:
            amount = float(input("Enter withdrawal amount: "))
            balance = connect.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()[0]

            if amount <= 0:
                print("Amount must be greater than 0. Please enter a valid amount.")
            elif amount > balance:
                print("Insufficient funds. Please enter a lower amount.")
            else:
                connect.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
                connect.execute("INSERT INTO transactions (user_id, amount) VALUES (?, ?)", (user_id, -amount))
                connect.commit()
                print("Withdrawal successful!")
                time.sleep(1)
                return
        except ValueError:
            print("Invalid input. Please enter a numeric amount.")


def transfer(user_id):
    while True:
        user_account = connect.execute("SELECT account_number FROM users WHERE id = ?", (user_id,)).fetchone()[0]

        while True:
            recipient_account = input("Enter recipient's account number: ").strip()
            if recipient_account == user_account:
                print("You cannot transfer money to yourself. Please enter a valid recipient account.")
            else:
                recipient = connect.execute("SELECT id FROM users WHERE account_number = ?", (recipient_account,)).fetchone()
                if recipient is None:
                    print("Recipient not found. Please enter a valid account number.")
                else:
                    break

        while True:
            try:
                amount = float(input("Enter transfer amount: "))
                if amount <= 0:
                    print("Transfer amount must be greater than 0.")
                else:
                    sender_balance = connect.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()[0]
                    if amount > sender_balance:
                        print("Insufficient funds. Please enter a lower amount.")
                    else:
                        recipient_id = recipient[0]
                        connect.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
                        connect.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, recipient_id))
                        connect.execute("INSERT INTO transactions (user_id, amount, recipient_account) VALUES (?, ?, ?)", 
                                        (user_id, -amount, recipient_account))
                        connect.execute("INSERT INTO transactions (user_id, amount, sender_account) VALUES (?, ?, ?)", 
                                        (recipient_id, amount, user_account))
                        connect.commit()
                        print("Transfer successful!")
                        time.sleep(1)
                        return
            except ValueError:
                print("Invalid input. Please enter a numeric amount.")

def transaction_history(user_id):
    transactions = connect.execute(
        "SELECT amount, sender_account, recipient_account, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC", 
        (user_id,)
    ).fetchall()

    print("************** Transaction History **************")
    
    if not transactions:
        print("No transactions found.")
    else:
        for amount, sender, recipient, timestamp in transactions:
            if sender and recipient:
                print(f"{timestamp} - Sent ₦{amount:.2f} to {recipient}" if amount < 0 else f"{timestamp} - Received ₦{abs(amount):.2f} from {sender}")
            else:
                print(f"{timestamp} - Deposit: ₦{amount:.2f}" if sender is None else f"{timestamp} - Withdrawal: ₦{abs(amount):.2f}")

def main_menu():
    while True:
        print("""
*************** Main Menu ***************
1. Sign Up
2. Log In
3. Quit
""")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            sign_up()
        elif choice == "2":
            log_in() 
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
        break

main_menu()
