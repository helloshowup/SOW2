import smtplib
from email.mime.multipart import MIMEMultipart

from app.email_sender import EmailSender

class DummySMTP:
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.started = False
        self.logged_in = False
        self.sent = False

    def starttls(self, context=None):
        self.started = True

    def login(self, username, password):
        self.logged_in = (username, password)

    def send_message(self, msg):
        self.sent_msg = msg
        self.sent = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

def test_send_summary_email(monkeypatch):
    dummy = DummySMTP("smtp.example.com", 587)
    monkeypatch.setattr(smtplib, "SMTP", lambda server, port: dummy)

    sender = EmailSender(
        smtp_server="smtp.example.com",
        smtp_port=587,
        username="user",
        password="pass",
        sender_email="sender@example.com",
        receiver_email="receiver@example.com",
    )

    summary = {
        "brand_health": [{"item": "Pizza", "score": 0.9}],
        "market_intelligence": [{"item": "Burgers", "score": 0.8}],
    }

    sender.send_summary_email(summary, run_id=1)

    assert dummy.started
    assert dummy.logged_in == ("user", "pass")
    assert dummy.sent
    assert isinstance(dummy.sent_msg, MIMEMultipart)
    body = dummy.sent_msg.as_string()
    assert "Brand Health Report" in body
    assert "Market Intelligence Briefing" in body
