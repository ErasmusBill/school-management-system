from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from src.config import Config
from fastapi import BackgroundTasks

# Configure email settings
conf = ConnectionConfig(
    MAIL_USERNAME=Config.MAIL_USERNAME,
    MAIL_PASSWORD=Config.MAIL_PASSWORD,
    MAIL_FROM=Config.MAIL_FROM,
    MAIL_PORT=Config.MAIL_PORT,
    MAIL_SERVER=Config.MAIL_SERVER,
    MAIL_FROM_NAME=Config.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# Create FastMail instance
fm = FastMail(conf)

async def send_welcome_email(email: str, password: str):
    """Send welcome email with credentials"""
    message = MessageSchema(
        recipients=[email],
        subject="Your New Account Credentials",
        body=f"""
        <h1>Welcome to Our Platform!</h1>
        <p>Your temporary password: <strong>{password}</strong></p>
        <p>Please change it after your first login.</p>
        """,
        subtype="html"
    )
    await fm.send_message(message)
    
async def send_serial_token(email: str, serial_token: str):
    """Send serial token email"""
    message = MessageSchema(
        recipients=[email],
        subject="Your Serial Token",
        body=f"""
        <h1>Your Serial Token</h1>
        <p>Your serial token: <strong>{serial_token}</strong></p>
        """,
        subtype="html"
    )
    await fm.send_message(message)    
    
async def send_approve_admission_email(email: str, admission_id: int):
    """Send admission approval email"""
    message = MessageSchema(
        recipients=[email],
        subject="Admission Approved",
        body=f"""
        <h1>Congratulations!</h1>
        <p>Your admission with ID: <strong>{admission_id}</strong> has been approved.</p>
        <p>You can now proceed with the registration process. Please log in to your account for the next steps.</p>
        """,
        subtype="html"
    )
    await fm.send_message(message)

async def send_decline_admission_email(email: str, admission_id: int):
    """Send admission decline email"""
    message = MessageSchema(
        recipients=[email],
        subject="Admission Application Update",
        body=f"""
        <h1>Admission Update</h1>
        <p>We regret to inform you that your admission application with ID: <strong>{admission_id}</strong> has been declined.</p>
        <p>Please contact our admissions office for more information or to discuss your options.</p>
        """,
        subtype="html"
    )
    await fm.send_message(message)