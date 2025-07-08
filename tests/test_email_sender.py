import os
import smtplib
from email.mime.multipart import MIMEMultipart

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test")

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

    sender.send_summary_email(
        run_id=1,
        on_brand_specific_links=["http://brand.com"],
        brand_relevant_links=["http://relevant.com"],
        brand_system_prompt="brand",
        market_system_prompt="market",
        user_prompt="user",
        search_terms_generated=["pizza"],
        num_search_calls=2,
        search_times=["t1", "t2"],
        content_summaries=["summary"],
    )

    assert dummy.started
    assert dummy.logged_in == ("user", "pass")
    assert dummy.sent
    assert isinstance(dummy.sent_msg, MIMEMultipart)
    body = dummy.sent_msg.as_string()
    assert "on brand specific" in body
    assert "brand relevant but not brand specific" in body
    assert "Brand System Prompt" in body
    assert "Number of Search Calls" in body

