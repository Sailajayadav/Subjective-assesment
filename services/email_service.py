from flask import current_app
from flask_mail import Message
import logging

logger = logging.getLogger(__name__)

# CHANGE: Added optional html_content parameter
def send_email(to_email, subject, body, html_content=None):
    """
    Sends an email using Flask-Mail, supporting both plain text (body) 
    and optional HTML content (html_content).
    """
    try:
        # Get the Mail instance and default sender from the Flask application context
        mail = current_app.extensions.get('mail')
        sender = current_app.config.get("MAIL_DEFAULT_SENDER")
        
        # CHANGE: Pass html_content to the 'html' parameter of Message
        # The 'body' argument remains the plain text fallback.
        msg = Message(
            subject=subject, 
            recipients=[to_email], 
            body=body, 
            html=html_content, # NEW: Pass the HTML content here
            sender=sender
        )
        
        mail.send(msg)
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.exception("Failed to send email")
        return False