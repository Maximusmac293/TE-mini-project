import re
import sqlite3
import csv
from datetime import datetime

messages = """
Sent Rs.160.00
From HDFC Bank A/C x6778
To Banglore iyangar bakery
On 28/03/25
Ref 102200374896
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.235.00
From HDFC Bank A/C x6778
To BOBBY MATHEWS JOHN
On 30/03/25
Ref 102306427195
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.438.00
From HDFC Bank A/C x6778
To RAHUL KUMAR  MAHTO
On 30/03/25
Ref 102332524687
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.20.00
From HDFC Bank A/C x6778
To UMA SHANKAR KUSHWAHA
On 28/03/25
Ref 102186595172
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.180.00
From HDFC Bank A/C x6778
To SUSHAMA VISHWAS PATIL
On 30/03/25
Ref 102310312659
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.10.00
From HDFC Bank A/C x6778
To NILESH DATTARAM PAWASKAR
On 28/03/25
Ref 102184283855
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.20.00
From HDFC Bank A/C x6778
To Sanjay Jiva Solanki
On 28/03/25
Ref 102183811244
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.30.00
From HDFC Bank A/C x6778
To NIKHIL BANWARILAL CHOURASIYA
On 27/03/25
Ref 102164587103
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808

Sent Rs.18.00
From HDFC Bank A/C x6778
To Mr Ram Nilesh Chaur
On 27/03/25
Ref 102158043741
Not You?
Call 18002586161/SMS BLOCK UPI to 7308080808
"""

def parse_upi_messages(message_text):
    message_blocks = message_text.strip().split('\n\n')
    
    transactions = []
    
    for block in message_blocks:
        lines = block.split('\n')
        transaction = {}
        
        for line in lines:
            # Parse amount
            if line.startswith('Sent Rs.'):
                amount = re.search(r'Sent Rs\.([\d,.]+)', line)
                if amount:
                    transaction['amount'] = float(amount.group(1).replace(',', ''))
            
            # Parse from account
            elif line.startswith('From '):
                from_match = re.match(r'From (.+)', line)
                if from_match:
                    transaction['from_account'] = from_match.group(1)
            
            # Parse recipient
            elif line.startswith('To '):
                to_match = re.match(r'To (.+)', line)
                if to_match:
                    transaction['to_recipient'] = to_match.group(1)
            
            # Parse date
            elif line.startswith('On '):
                date_match = re.match(r'On (\d{2}/\d{2}/\d{2})', line)
                if date_match:
                    date_str = date_match.group(1)
                    # Convert date to YYYY-MM-DD format
                    transaction['date'] = datetime.strptime(date_str, '%d/%m/%y').strftime('%Y-%m-%d')
            
            # Parse reference number
            elif line.startswith('Ref '):
                ref_match = re.match(r'Ref (\d+)', line)
                if ref_match:
                    transaction['reference_number'] = ref_match.group(1)
        
        if transaction:  # Only add if we found data
            transactions.append(transaction)
    
    return transactions

def create_database():
    conn = sqlite3.connect('upi_transactions.db')
    c = conn.cursor()
    
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  amount REAL,
                  from_account TEXT,
                  to_recipient TEXT,
                  date TEXT,
                  reference_number TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def save_to_database(transactions):
    conn = sqlite3.connect('upi_transactions.db')
    c = conn.cursor()
    
    for txn in transactions:
        c.execute('''INSERT INTO transactions 
                    (amount, from_account, to_recipient, date, reference_number)
                    VALUES (?, ?, ?, ?, ?)''',
                 (txn['amount'], txn['from_account'], txn['to_recipient'], 
                  txn['date'], txn['reference_number']))
    
    conn.commit()
    conn.close()

def generate_csv(output_file='upi_transactions.csv'):
    conn = sqlite3.connect('upi_transactions.db')
    c = conn.cursor()
    
    # Get all transactions
    c.execute('''SELECT date, amount, from_account, to_recipient, reference_number 
                 FROM transactions ORDER BY date''')
    transactions = c.fetchall()
    
    # Write to CSV
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['Date', 'Amount', 'From Account', 'To Recipient', 'Reference Number'])
        # Write data
        writer.writerows(transactions)
    
    conn.close()
    print(f"CSV file generated: {output_file}")

def main():
    # Parse the messages
    transactions = parse_upi_messages(messages)
    
    # Set up database
    create_database()
    
    # Save to database
    save_to_database(transactions)
    
    # Generate CSV
    generate_csv()
    
    print(f"Processed {len(transactions)} transactions.")

if __name__ == "__main__":
    main()