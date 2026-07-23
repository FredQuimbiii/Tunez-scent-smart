import os
import smtplib
import threading
from email.message import EmailMessage

my_email = "tunezscentmart@gmail.com"
password = os.environ.get('EMAIL_PAS')

def _send(msg):
    with smtplib.SMTP_SSL(host="smtp.gmail.com", port=465) as connection:
        connection.login(user=my_email, password=password)
        connection.send_message(msg)

def place_order(message):
    msg = EmailMessage()
    msg["Subject"] = "New Order"
    msg["From"] = my_email
    msg["To"] = "tunezscentmart@gmail.com"
    msg.set_content(message)
    threading.Thread(target=_send, args=(msg,)).start()

def send_order_confirmation(message, cus_name, cus_mail):
    msg = EmailMessage()
    msg["Subject"] = "Your Tunez Scent Mart Order Confirmation"
    msg["From"] = my_email
    msg["To"] = cus_mail
    msg.set_content(f"Hi {cus_name},\n\n{message}")
    threading.Thread(target=_send, args=(msg,)).start()

def send_otp(otp_code, cus_name, cus_mail):
    msg = EmailMessage()
    msg["Subject"] = "Your Verification Code"
    msg["From"] = my_email
    msg["To"] = cus_mail
    msg.set_content(f"Hello {cus_name},\n\nYour verification code is: {otp_code}\n\nThis code expires in 10 minutes.")
    threading.Thread(target=_send, args=(msg,)).start()