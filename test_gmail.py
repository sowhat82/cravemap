import smtplib
from email.mime.text import MIMEText

# Test Gmail SMTP directly
def test_gmail_auth():
    try:
        print("Testing Gmail SMTP authentication...")
        
        # Your credentials
        email = "alvinandsamantha@gmail.com"
        password = "eyxn fzqe reed ksyg"
        
        print(f"Email: {email}")
        print(f"Password length: {len(password)}")
        print(f"Password ends with: {password[-4:]}")
        
        # Test connection
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        
        print("Attempting login...")
        server.login(email, password)
        print("✅ Login successful!")
        
        server.quit()
        return True
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False

if __name__ == "__main__":
    test_gmail_auth()
