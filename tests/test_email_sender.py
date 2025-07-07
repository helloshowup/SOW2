import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import types

import app.email_sender as email_sender

class DummySMTP:
    last = None
    def __init__(self, server, port):
        DummySMTP.last = self
        self.server = server
        self.port = port
        self.started = False
        self.logged_in = False
        self.sent = False
    def starttls(self, context=None):
        self.started = True
    def login(self, user, pwd):
        self.logged_in = True
    def send_message(self, msg):
        self.sent = True
        self.message = msg
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass


def test_send_summary_email_success(monkeypatch):
    DummySMTP.last = None
    monkeypatch.setattr(email_sender, "smtplib", types.SimpleNamespace(SMTP=DummySMTP))
    monkeypatch.setattr(email_sender.config, "SMTP_SERVER", "smtp")
    monkeypatch.setattr(email_sender.config, "SMTP_PORT", 587)
    monkeypatch.setattr(email_sender.config, "SMTP_USERNAME", "u")
    monkeypatch.setattr(email_sender.config, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(email_sender.config, "SENDER_EMAIL", "s@example.com")
    monkeypatch.setattr(email_sender.config, "RECEIVER_EMAIL", "r@example.com")
    monkeypatch.setattr(email_sender.config, "FEEDBACK_BASE_URL", "http://x")
    results = [{"item": "A", "score": 1}]
    email_sender.send_summary_email(results, 1)
    smtp = DummySMTP.last
    assert smtp.sent
    assert "AI Agent Daily Summary" in smtp.message["Subject"]


def test_send_summary_email_missing_config(monkeypatch):
    DummySMTP.last = None
    monkeypatch.setattr(email_sender, "smtplib", types.SimpleNamespace(SMTP=DummySMTP))
    monkeypatch.setattr(email_sender.config, "SMTP_SERVER", "")
    monkeypatch.setattr(email_sender.config, "SMTP_USERNAME", "")
    monkeypatch.setattr(email_sender.config, "SMTP_PASSWORD", "")
    monkeypatch.setattr(email_sender.config, "SENDER_EMAIL", "")
    monkeypatch.setattr(email_sender.config, "RECEIVER_EMAIL", "")
    email_sender.send_summary_email([], 1)
    smtp = DummySMTP.last
    assert smtp is None
