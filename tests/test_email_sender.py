import smtplib
from email.mime.multipart import MIMEMultipart

import pytest

from app import email_sender

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
    monkeypatch.setattr(email_sender, "SMTP_SERVER", "smtp.example.com")
    monkeypatch.setattr(email_sender, "SMTP_PORT", 587)
    monkeypatch.setattr(email_sender, "SMTP_USERNAME", "user")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "pass")
    monkeypatch.setattr(email_sender, "SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(email_sender, "RECEIVER_EMAIL", "receiver@example.com")

    dummy = DummySMTP("smtp.example.com", 587)
    monkeypatch.setattr(smtplib, "SMTP", lambda server, port: dummy)

    email_sender.send_summary_email([{"item": "Pizza", "score": 0.9}], run_id=1)

    assert dummy.started
    assert dummy.logged_in == ("user", "pass")
    assert dummy.sent
    assert isinstance(dummy.sent_msg, MIMEMultipart)

