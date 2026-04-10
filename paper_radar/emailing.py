from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_email_with_attachments(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    attachment_paths: list[str | Path],
) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM", username)

    if not all([host, port, username, password, mail_from, to_email]):
        raise RuntimeError("Missing SMTP settings or recipient.")

    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("This message contains an HTML literature radar report.")
    msg.add_alternative(html_body, subtype="html")

    for path in attachment_paths:
        path = Path(path)
        if not path.exists():
            continue
        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        with open(path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
