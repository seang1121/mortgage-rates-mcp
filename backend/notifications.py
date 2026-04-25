"""Alert delivery — Discord webhook + email. Triggered post-scrape.

After each 7am/7pm scrape:
  1. Query all active alerts
  2. Compare against new rates
  3. Dispatch through user's configured channels
  4. Update last_triggered_at to prevent spam
"""
import json
import os
import smtplib
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText

from backend.database import db
from backend.extractors.base import PRODUCT_DISPLAY_NAMES


def check_and_send_alerts():
    """Check all active alerts against current rates and dispatch notifications."""
    alerts = db.query(
        """SELECT ra.*, u.email
           FROM rate_alerts ra
           JOIN users u ON ra.user_id = u.id
           WHERE ra.active = 1"""
    )
    if not alerts:
        return

    current_rates = db.query("SELECT * FROM rates WHERE stale = 0")
    triggered_count = 0

    for alert in alerts:
        # Find rates that meet the threshold
        matching = [
            r for r in current_rates
            if r['product'] == alert['product']
            and (alert['lender'] is None or r['lender'] == alert['lender'])
            and r['rate'] <= alert['threshold']
            and not r['is_benchmark']
        ]

        if not matching:
            continue

        # Don't re-trigger within 12 hours
        if alert.get('last_triggered_at'):
            try:
                last = datetime.fromisoformat(alert['last_triggered_at'])
                if (datetime.now() - last).total_seconds() < 43200:
                    continue
            except Exception:
                pass

        # Build alert message
        message = _format_alert(alert, matching)

        # Get user notification preferences
        prefs = db.query(
            "SELECT * FROM notification_preferences WHERE user_id = ? AND active = 1",
            (alert['user_id'],)
        )

        sent = False
        for pref in prefs:
            if pref['channel'] == 'discord_webhook':
                _send_discord(pref['destination'], message)
                sent = True
            elif pref['channel'] == 'email':
                _send_email(pref['destination'], "Mortgage Rate Alert", message)
                sent = True

        # Fallback: email from user record if no prefs configured
        if not sent and alert.get('email'):
            _send_email(alert['email'], "Mortgage Rate Alert", message)

        # Mark as triggered
        db.execute(
            "UPDATE rate_alerts SET last_triggered_at = ? WHERE id = ?",
            (datetime.now().isoformat(), alert['id'])
        )
        triggered_count += 1

    if triggered_count:
        print(f"[ALERTS] Triggered {triggered_count} alerts")


def _format_alert(alert, matching_rates) -> str:
    """Format a rate alert notification — clear, actionable."""
    product_name = PRODUCT_DISPLAY_NAMES.get(alert['product'], alert['product'])
    lines = [
        f"Rate Alert: {product_name} dropped below {alert['threshold']}%",
        "",
    ]
    for r in sorted(matching_rates, key=lambda x: x['rate']):
        apr_str = f" ({r['apr']:.3f}% APR)" if r.get('apr') else ""
        lines.append(f"  {r['lender']}: {r['rate']:.3f}%{apr_str}")

    lines.append("")
    lines.append(f"As of {datetime.now().strftime('%I:%M %p EST on %m/%d/%Y')}")
    lines.append("")
    lines.append("Publicly advertised rates, not personalized quotes.")
    return "\n".join(lines)


def _send_discord(webhook_url: str, message: str):
    """Send alert via Discord webhook. Cloudflare in front of discord.com
    rejects urllib's default User-Agent (error 1010), so we set one."""
    try:
        data = json.dumps({"content": f"```\n{message}\n```"}).encode()
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "mortgage-rates-mcp (+https://github.com/seang1121/mortgage-rates-mcp)",
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[ALERTS] Discord send failed: {e}")


def send_discord_alert(message: str):
    """Send system alert to admin Discord webhook (scrape failures, etc.)."""
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook:
        _send_discord(webhook, message)


def _send_email(to_addr: str, subject: str, body: str):
    """Send alert via SMTP email."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")

    if not user or not password:
        print(f"[ALERTS] Email not configured, skipping alert to {to_addr}")
        return

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
    except Exception as e:
        print(f"[ALERTS] Email send failed to {to_addr}: {e}")
