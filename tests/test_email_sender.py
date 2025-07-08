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
        on_brand_specific_links=[{"url": "http://brand.com", "snappy_heading": "Brand"}],
        brand_relevant_links=[{"url": "http://relevant.com", "snappy_heading": "Relevant"}],
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
    body_raw = dummy.sent_msg.get_payload()[0].get_payload(decode=True).decode()
    assert "on brand specific" in body_raw
    assert "brand relevant but not brand specific" in body_raw
    assert "Brand System Prompt" in body_raw
    assert "Number of Search Calls" in body_raw

