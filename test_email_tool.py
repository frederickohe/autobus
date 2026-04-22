"""Test script for EmailTool with Zeptomail functionality"""

import sys
import os
from pathlib import Path

# Add src to path to import from core
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.agent.tools.email.email import EmailTool


def test_zeptomail_send():
    """Test the Zeptomail SMTP sending functionality"""
    
    # Initialize EmailTool with default config
    email_tool = EmailTool()
    
    # Test parameters
    sender_email = "noreply@useautobus.com"
    to_email = "cto@greenbraintech.com"
    subject = "Test Email from Autobus"
    body = "Hello! This is a test email from the Autobus email tool."
    
    print("=" * 60)
    print("Testing EmailTool._send_via_zeptomail()")
    print("=" * 60)
    print(f"Sender: {sender_email}")
    print(f"Recipient: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print("-" * 60)
    
    # Call the _send_via_zeptomail method
    try:
        result = email_tool._send_via_zeptomail(
            sender_email=sender_email,
            to_email=to_email,
            subject=subject,
            body=body
        )
        
        if result:
            print("✅ Email sent successfully!")
            print(f"Result: {result}")
        else:
            print("❌ Email sending failed")
            print("Check your Zeptomail SMTP credentials and environment variables:")
            print(f"  - ZEPTOMAIL_SMTP_HOST")
            print(f"  - ZEPTOMAIL_SMTP_PORT")
            print(f"  - ZEPTOMAIL_SMTP_USERNAME")
            print(f"  - ZEPTOMAIL_SMTP_PASSWORD")
            
    except Exception as e:
        print(f"❌ Error occurred: {type(e).__name__}: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Verify ZEPTOMAIL_SMTP_PASSWORD is set in environment")
        print("  2. Check if the sender email is verified in Zeptomail")
        print("  3. Ensure network connectivity to smtp.zeptomail.com")


def test_zeptomail_with_html():
    """Test Zeptomail with HTML email content"""
    
    email_tool = EmailTool()
    
    sender_email = "noreply@greenbraintech.com"
    to_email = "user@example.com"
    subject = "Test HTML Email"
    body = """
    <html>
        <body>
            <h1>Welcome to Autobus!</h1>
            <p>This is an <strong>HTML formatted</strong> test email.</p>
            <a href="https://useautobus.com">Click here</a> to learn more.
        </body>
    </html>
    """
    
    print("\n" + "=" * 60)
    print("Testing EmailTool._send_via_zeptomail() with HTML content")
    print("=" * 60)
    print(f"Sender: {sender_email}")
    print(f"Recipient: {to_email}")
    print(f"Subject: {subject}")
    print("-" * 60)
    
    try:
        result = email_tool._send_via_zeptomail(
            sender_email=sender_email,
            to_email=to_email,
            subject=subject,
            body=body
        )
        
        if result:
            print("✅ HTML email sent successfully!")
        else:
            print("❌ HTML email sending failed")
            
    except Exception as e:
        print(f"❌ Error occurred: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("Starting EmailTool tests...\n")
    
    # Check if required environment variables are set
    required_env_vars = [
        'ZEPTOMAIL_SMTP_HOST',
        'ZEPTOMAIL_SMTP_PORT',
        'ZEPTOMAIL_SMTP_USERNAME',
        'ZEPTOMAIL_SMTP_PASSWORD'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️  WARNING: Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nTests will likely fail without these configured.")
        print("-" * 60 + "\n")
    
    # Run tests
    test_zeptomail_send()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
