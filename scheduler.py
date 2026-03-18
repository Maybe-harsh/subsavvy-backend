import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import SessionLocal
import models
from recommendation import generate_alerts_for_user

# --- LOAD HIDDEN CREDENTIALS ---
# This automatically finds your .env file and loads the variables
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

def send_email(to_email, subject, body):
    # Failsafe: Don't try to send if credentials are missing
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("❌ ERROR: Email credentials not found in .env file. Cannot send alert.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = f"SubSavvy AI <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach the HTML body
        msg.attach(MIMEText(body, 'html'))

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # Secure the connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"📧 SUCCESS: Sent AI alert email to {to_email}")
    except Exception as e:
        print(f"❌ ERROR: Failed to send email to {to_email}. Details: {e}")

def run_daily_ai_recommendations():
    """This function runs automatically on a schedule."""
    print("🕒 [CRON JOB STARTED] Running daily AI analysis and email alerts...")
    
    # Open a fresh database session
    db: Session = SessionLocal()
    
    try:
        # Fetch all active users
        users = db.query(models.User).all()
        
        for user in users:
            print(f"Analyzing data for user: {user.email}")
            
            # 1. Call the AI function we wrote earlier
            alerts = generate_alerts_for_user(db, str(user.id))
            
            # 2. Filter out the "success" messages. We only email if they are wasting money!
            urgent_alerts = [a for a in alerts if a['type'] in ['alert', 'warning']]
            
            if urgent_alerts:
                # 3. Format a beautiful HTML email
                html_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333; background-color: #f9fafb; padding: 20px; border-radius: 10px;">
                    <h2 style="color: #6366f1;">SubSavvy Financial Alert ✨</h2>
                    <p>Hi {user.email},</p>
                    <p>Our AI has detected some inefficiencies in your streaming portfolio. Here is what we found based on your recent watch time:</p>
                    <ul style="line-height: 1.6; background-color: white; padding: 20px; border-radius: 8px; border: 1px solid #e5e7eb;">
                """
                
                for alert in urgent_alerts:
                    html_content += f"<li style='margin-bottom: 10px;'><b>{alert['platform']}:</b> {alert['message']}</li>"
                
                html_content += """
                    </ul>
                    <p style="margin-top: 20px; text-align: center;">
                        <a href="http://localhost:3000/dashboard" style="background-color: #d946ef; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                            Open Dashboard to Optimize
                        </a>
                    </p>
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                    <p style="font-size: 12px; color: #9ca3af; text-align: center;">You are receiving this because you enabled AI tracking on SubSavvy.</p>
                </div>
                """
                
                send_email(user.email, "Action Required: Unused Subscriptions Detected", html_content)
            else:
                print(f"✅ {user.email} is fully optimized. No email sent.")
                
        print("✅ [CRON JOB FINISHED] AI recommendations and emails processed successfully.")
        
    except Exception as e:
        print(f"❌ [CRON JOB ERROR] {e}")
    finally:
        db.close()

# Initialize the scheduler
task_scheduler = BackgroundScheduler()

# --- PRODUCTION SCHEDULE ---
# Runs exactly once a day at 8:00 AM
task_scheduler.add_job(
    run_daily_ai_recommendations, 
    'cron', 
    hour=8, 
    minute=0
)

def start_scheduler():
    task_scheduler.start()
    print("⏰ SubSavvy AI Background Email Scheduler Started (Daily at 8:00 AM)!")