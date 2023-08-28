import imaplib
import email
import os
from datetime import datetime
from bs4 import BeautifulSoup
import re

from firebase_admin.db import Query

from transaction import Transaction
from dotenv import load_dotenv

load_dotenv()

email_bco_chile = 'enviodigital@bancochile.cl'

def fetch_gmail_emails(username, password, user_id):
    # Connect to Gmail's IMAP server
    imap_server = imaplib.IMAP4_SSL('imap.gmail.com')

    try:
        # Login with your credentials
        imap_server.login(username, password)

        # Select the mailbox you want to fetch emails from (e.g., 'INBOX')
        imap_server.select('INBOX')

        # Search for all emails in the selected mailbox
        status, messages = imap_server.search(None, "(FROM {})".format(email_bco_chile))
        if status == 'OK':
            # List of email IDs returned as bytes; convert to a list of integers
            email_ids = [int(x) for x in messages[0].split()]
            email_ids.reverse()
            for email_id in email_ids:
                # Fetch the email using the unique ID
                status, msg_data = imap_server.fetch(str(email_id), '(RFC822)')

                if status == 'OK':
                    # 'msg_data' is a list containing the raw email data; extract the message content
                    activity, amount, name, timestamp, type = process_email(msg_data)
                    if amount is None or timestamp is None:
                        continue
                    try:
                        tr = Transaction(activity,
                                         float(amount.replace('$', '').replace('.', '').replace(',', '.')),
                                         name,
                                         datetime.strptime(timestamp, '%d/%m/%Y %H:%M'),
                                         type,
                                         None,
                                         user_id)
                        print("Persisted: " + str(tr.persisted()))
                        tr.persist()
                        print("TX: " + str(tr))

                    except Exception as N:
                        print(N)
                        print("FALLO")
                        print("Activity:", activity)
                        print("Amount:", amount)
                        print("Name:", name)
                        print("Timestamp:", timestamp)
    except Exception as e:
        print("Error: {}".format(e))

    finally:
        # Logout from the server
        imap_server.logout()


def process_email(msg_data):
    raw_email = msg_data[0][1]
    email_message = email.message_from_bytes(raw_email)
    # Extract various email properties (e.g., Body)
    email_body = email_message.get_payload()[0].as_string()
    email_text = BeautifulSoup(email_body, 'html.parser').get_text().replace("=\n", '')
    activity, amount, name, timestamp, type = extract_info_from_body(email_text)
    return activity, amount, name, timestamp, type


def extract_info_from_body(body):
    # Regex patterns
    activity_pattern = r'(\b\w+\b)\s+por'  # Matches the activity before "por"
    amount_pattern = r'\$[\d,.]+'  # Matches amounts like $8.756 or $1,234.56
    name_pattern = r'en\s(.+?)\sel'  # Matches name between 'en' and 'el'
    timestamp_pattern = r'el\s(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2})'  # Matches timestamp in format dd/mm/yyyy HH:MM
    credito_pattern = r'Tarjeta de Crédito'

    # Extracting information using regex
    activity_match = re.search(activity_pattern, body)
    amount_match = re.search(amount_pattern, body)
    name_match = re.search(name_pattern, body)
    timestamp_match = re.search(timestamp_pattern, body)
    credito_match = re.search(credito_pattern, body)

    # Retrieving matched information
    activity = activity_match.group(1) if activity_match else None
    amount = amount_match.group() if amount_match else None
    name = name_match.group(1) if name_match and activity == 'compra' else None
    timestamp = timestamp_match.group(1) if timestamp_match else None
    type = 'credito' if credito_match else 'debito'
    if amount is None:
        return None, None, None, None, None
    return activity, amount, name, timestamp, type


# print(f"Data saved to Firebase with key: {new_data_entry.key}")
# Replace 'your_username' and 'your_password' with your Gmail credentials
username = os.environ['EMAIL']
password = os.environ['EMAILPASSWORD']
user_id = os.environ["USERID"]

fetch_gmail_emails(username, password, user_id)
