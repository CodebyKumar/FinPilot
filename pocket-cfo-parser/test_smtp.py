#!/usr/bin/env python3
"""Direct SMTP test to debug email configuration."""

import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "").strip()
REMINDER_EMAIL_TO = os.getenv("REMINDER_EMAIL_TO", "").strip()

print("=" * 60)
print("SMTP Configuration Check")
print("=" * 60)
print(f"Host: {SMTP_HOST}")
print(f"Port: {SMTP_PORT}")
print(f"Username: {SMTP_USERNAME}")
print(f"Password: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else '(empty)'}")
print(f"From Email: {SMTP_FROM_EMAIL}")
print(f"To Email: {REMINDER_EMAIL_TO}")
print("=" * 60)

if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL, REMINDER_EMAIL_TO]):
    print("ERROR: Missing SMTP configuration in .env")
    exit(1)

try:
    print("\n[1] Connecting to SMTP server...")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
    print(f"✓ Connected to {SMTP_HOST}:{SMTP_PORT}")
    
    print("\n[2] Starting TLS...")
    server.starttls()
    print("✓ TLS started")
    
    print(f"\n[3] Logging in as {SMTP_USERNAME}...")
    try:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print("✓ Login successful")
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ LOGIN FAILED: {e}")
        print("\nNote: Gmail requires an App Password, not regular password")
        print("Go to: https://myaccount.google.com/apppasswords")
        print("Create an 'Mail' app password and use that instead")
        exit(1)
    
    print("\n[4] Creating test email...")
    msg = EmailMessage()
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = REMINDER_EMAIL_TO
    msg["Subject"] = "Pocket CFO SMTP Test"
    msg.set_content("This is a test email to verify SMTP configuration works.")
    print(f"✓ Email created: {SMTP_FROM_EMAIL} -> {REMINDER_EMAIL_TO}")
    
    print("\n[5] Sending email...")
    server.send_message(msg)
    print("✓ Email sent successfully!")
    
    server.quit()
    print("\n" + "=" * 60)
    print("SUCCESS: Email configuration is working!")
    print("=" * 60)

except smtplib.SMTPException as e:
    print(f"✗ SMTP Error: {e}")
    exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
