import os
import resend

resend.api_key = os.environ.get('RESEND_API_KEY')

my_email = "tunezscentmart@gmail.com"

def place_order(message):
    resend.Emails.send({
        "from": "Tunez Scent Mart <rajiabdulkadir15@gmail.com>",
        "to": [my_email],
        "subject": "New Order",
        "text": message,
    })

def send_order_confirmation(message, cus_name, cus_mail):
    resend.Emails.send({
        "from": "Tunez Scent Mart <rajiabdulkadir15@gmail.com>",
        "to": [cus_mail],
        "subject": "Your Tunez Scent Mart Order Confirmation",
        "text": f"Hi {cus_name},\n\n{message}",
    })

def send_otp(otp_code, cus_name, cus_mail):
    resend.Emails.send({
        "from": "Tunez Scent Mart <rajiabdulkadir15@gmail.com>",
        "to": [cus_mail],
        "subject": "Your Verification Code",
        "text": f"Hello {cus_name},\n\nYour verification code is: {otp_code}\n\nThis code expires in 10 minutes.",
    })