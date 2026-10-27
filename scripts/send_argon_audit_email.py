#!/usr/bin/env python3
"""
SolarSense EMS — Email Dispatcher for Argon Audit Review.
Prepares and dispatches the complete Argon review prompt along with the
solarsense_argon_audit_bundle.zip archive to the user's email address.

Supported modes:
  1. EML File Export: Generates a complete RFC 822 .eml file that opens in any mail client.
  2. Thunderbird GUI: Automatically launches Thunderbird with recipient, subject, body, and attachment.
  3. Direct SMTP: Dispatches directly via Gmail SMTP (port 587 STARTTLS) if an App Password is provided.
"""

import argparse
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from pathlib import Path
import smtplib
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_PATH = REPO_ROOT / "solarsense_argon_audit_bundle.zip"
PROMPT_PATH = REPO_ROOT / "docs" / "ARGON_AUDIT_PROMPT.md"
DEFAULT_RECIPIENT = "abubakariqbal651@gmail.com"
DEFAULT_SUBJECT = "SolarSense EMS — Station 904-A JT Audit Bundle & Review Prompt for Argon"


def build_mime_message(
    recipient: str,
    subject: str,
    body_text: str,
    attachment_path: Path,
) -> MIMEMultipart:
    """Construct a full MIME multipart message with text body and zip attachment."""
    msg = MIMEMultipart()
    msg["From"] = recipient
    msg["To"] = recipient
    msg["Subject"] = subject

    # Attach prompt text
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    # Attach zip archive
    if attachment_path.exists():
        part = MIMEBase("application", "zip")
        with open(attachment_path, "rb") as f:
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{attachment_path.name}"',
        )
        msg.attach(part)
    else:
        print(f"[WARNING] Attachment {attachment_path} not found.")

    return msg


def save_eml_file(msg: MIMEMultipart, output_path: Path) -> Path:
    """Export the message to an RFC 822 .eml file."""
    with open(output_path, "wb") as f:
        f.write(msg.as_bytes())
    return output_path


def launch_thunderbird_compose(recipient: str, subject: str, body_text: str, attachment_path: Path) -> bool:
    """Launch Thunderbird compose window with pre-filled fields and attachment."""
    try:
        # Thunderbird compose argument formatting
        compose_args = f"to='{recipient}',subject='{subject}',attachment='{attachment_path.resolve()}'"
        
        # Save temp body file to avoid command-line length limits
        temp_body = REPO_ROOT / ".thunderbird_body_tmp.txt"
        temp_body.write_text(body_text, encoding="utf-8")
        compose_args += f",message='{temp_body.resolve()}'"

        cmd = ["thunderbird", "-compose", compose_args]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to launch Thunderbird: {e}", file=sys.stderr)
        return False


def send_via_smtp(
    recipient: str,
    sender: str,
    password: str,
    msg: MIMEMultipart,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> bool:
    """Send email via SMTP with STARTTLS authentication."""
    try:
        print(f"Connecting to {smtp_server}:{smtp_port} ...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        print(f"Authenticating as {sender} ...")
        server.login(sender, password)
        print("Sending message ...")
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print("[SUCCESS] Email sent successfully via SMTP!")
        return True
    except Exception as e:
        print(f"[ERROR] SMTP dispatch failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Dispatch Argon audit bundle and prompt via email.")
    parser.add_argument("--to", default=DEFAULT_RECIPIENT, help=f"Recipient email address (default: {DEFAULT_RECIPIENT})")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT, help="Email subject")
    parser.add_argument("--password", default=os.getenv("GMAIL_APP_PASSWORD", ""), help="Gmail App Password for direct SMTP")
    parser.add_argument("--thunderbird", action="store_true", help="Launch Thunderbird compose window")
    parser.add_argument("--eml", action="store_true", default=True, help="Generate .eml message file")

    args = parser.parse_args()

    # Load prompt text
    if not PROMPT_PATH.exists():
        print(f"[ERROR] Prompt file {PROMPT_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")

    # Verify bundle
    if not BUNDLE_PATH.exists():
        print(f"[ERROR] Bundle archive {BUNDLE_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("   SOLARSENSE EMS — EMAIL DISPATCHER FOR ARGON REVIEW")
    print("=" * 80)
    print(f"  • Recipient:   {args.to}")
    print(f"  • Subject:     {args.subject}")
    print(f"  • Attachment:  {BUNDLE_PATH} ({BUNDLE_PATH.stat().st_size / (1024*1024):.2f} MB)")
    print(f"  • Prompt Body: {PROMPT_PATH} ({len(prompt_text.splitlines())} lines)")
    print("=" * 80)

    # 1. Build MIME message
    msg = build_mime_message(args.to, args.subject, prompt_text, BUNDLE_PATH)

    # 2. Export EML file
    eml_path = REPO_ROOT / "solarsense_argon_audit_bundle.eml"
    save_eml_file(msg, eml_path)
    print(f"\n[OK] Standard RFC 822 email file created: {eml_path}")
    print("     (Double-click or open in Thunderbird/Gmail/Mail to send with 1 click)")

    # 3. Direct SMTP if password is provided
    if args.password:
        send_via_smtp(args.to, args.to, args.password, msg)
    else:
        print("\n[INFO] No Gmail App Password provided for direct background SMTP.")
        print("       To send directly in background: run with --password <YOUR_GMAIL_APP_PASSWORD>")
        print("       Or set GMAIL_APP_PASSWORD=<YOUR_GMAIL_APP_PASSWORD>")

    # 4. Launch Thunderbird if requested or desktop available
    if args.thunderbird or os.getenv("DISPLAY"):
        print("\nAttempting to open email composer in Thunderbird ...")
        success = launch_thunderbird_compose(args.to, args.subject, prompt_text, BUNDLE_PATH)
        if success:
            print("[OK] Thunderbird compose window initiated!")

    print("\n" + "=" * 80)
    print("   DISPATCH COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
