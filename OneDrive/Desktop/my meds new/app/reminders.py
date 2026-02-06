import smtplib
from email.message import EmailMessage
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app.models import db, Medicine, ReminderQueue, User
from app.config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = Config.SMTP_USER
    msg['To'] = to_email

    try:
        if not Config.SMTP_USER or not Config.SMTP_PASS:
            logger.warning("SMTP credentials not set. Skipping email.")
            return False

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def scan_and_queue_reminders(app):
    """
    Scans medicines and ensures ReminderQueue has entries for upcoming doses.
    For simplicity, look at today's schedule and check if queued.
    """
    with app.app_context():
        now = datetime.utcnow()
        # Look ahead 24 hours
        end_time = now + timedelta(hours=24)
        
        medicines = Medicine.query.all()
        for med in medicines:
            times = med.get_times_list()
            if not times: continue
            
            # Simple check for "today" and "tomorrow" in UTC
            # This is a naive implementation. Correct way is to generate all occurrences between now and end_time
            # and check if they exist in ReminderQueue
            
            check_days = [now.date(), (now + timedelta(days=1)).date()]
            
            for day in check_days:
                for time_str in times:
                    try:
                        h, m = map(int, time_str.split(':'))
                        # Construct scheduled datetime
                        scheduled_dt = datetime.combine(day, datetime.min.time()).replace(hour=h, minute=m)
                        
                        if scheduled_dt < now:
                            continue # Already passed
                            
                        if scheduled_dt > end_time:
                            continue # Too far ahead
                            
                        # Check existence
                        exists = ReminderQueue.query.filter_by(
                            medicine_id=med.id, 
                            send_at=scheduled_dt
                        ).first()
                        
                        if not exists:
                            item = ReminderQueue(medicine_id=med.id, send_at=scheduled_dt)
                            db.session.add(item)
                    except:
                        continue
            db.session.commit()

def process_reminder_queue(app):
    """
    Sends pending emails.
    """
    with app.app_context():
        now = datetime.utcnow()
        # Find pending items where send_at <= now
        pending = ReminderQueue.query.filter(
            ReminderQueue.send_at <= now,
            ReminderQueue.sent == False,
            ReminderQueue.attempts < 3
        ).all()
        
        for item in pending:
            item.attempts += 1
            med = db.session.get(Medicine, item.medicine_id)
            user = db.session.get(User, med.user_id)
            
            subject = f"MyMeds Reminder: {med.name} at {item.send_at.strftime('%H:%M')}"
            body = f"Hello {user.name},\n\nIt's time to take your {med.name} ({med.dose}).\n\nPlease log it in your dashboard."
            
            if send_email(user.email, subject, body):
                item.sent = True
                logger.info(f"Sent reminder for {med.name} to {user.email}")
            else:
                logger.error(f"Failed to send reminder for {med.name}")
                
            db.session.commit()

def start_scheduler(app):
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler = BackgroundScheduler()
        # Scan every minute
        scheduler.add_job(lambda: scan_and_queue_reminders(app), 'interval', minutes=1)
        # Process queue every minute (offset by 30s to avoid DB lock contention ideally, but simultaneous is fine for sqlite WAL)
        scheduler.add_job(lambda: process_reminder_queue(app), 'interval', minutes=1)
        scheduler.start()
        logger.info("Scheduler started")