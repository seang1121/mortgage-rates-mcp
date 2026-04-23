"""Scraper scheduler — 7:00 AM and 7:00 PM EST daily.

After each scrape, checks rate alerts and sends notifications.
"""
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

scheduler = None


def _scrape_job():
    """Run scrape and check alerts post-scrape."""
    from backend.scraper import run_scrape

    # Jitter removed — was time.sleep() in the APScheduler worker, which
    # could collide with misfire_grace_time=600 and cause skipped runs.
    print(f"[SCHEDULER] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Starting scheduled scrape")
    try:
        result = run_scrape()
        print(f"[SCHEDULER] Complete: {result['total_rates']} rates, "
              f"{len(result['successes'])} succeeded, {len(result['failures'])} failed")

        if result['failures']:
            print(f"[SCHEDULER] Failures: {', '.join(result['failures'])}")

            # Alert admin if 3+ lenders failed
            if len(result['failures']) >= 3:
                try:
                    from backend.notifications import send_discord_alert
                    send_discord_alert(
                        f"Scrape degradation: {len(result['failures'])} lenders failed\n"
                        f"Failed: {', '.join(result['failures'])}"
                    )
                except Exception:
                    pass

        # Check rate alerts post-scrape
        try:
            from backend.notifications import check_and_send_alerts
            check_and_send_alerts()
        except Exception as e:
            print(f"[SCHEDULER] Alert check failed: {e}")

    except Exception as e:
        print(f"[SCHEDULER] Scrape failed: {e}")
        import traceback
        traceback.print_exc()


def start_scheduler():
    """Start the 7am/7pm EST scrape scheduler."""
    global scheduler

    if scheduler is not None:
        print("[SCHEDULER] Already running")
        return

    scheduler = BackgroundScheduler(timezone=pytz.timezone('US/Eastern'))

    # 7:00 AM EST — morning scrape
    scheduler.add_job(
        _scrape_job,
        trigger=CronTrigger(hour=7, minute=0, timezone='US/Eastern'),
        id='morning_scrape',
        name='Morning rate scrape (7am EST)',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600,
    )

    # 7:00 PM EST — evening scrape
    scheduler.add_job(
        _scrape_job,
        trigger=CronTrigger(hour=19, minute=0, timezone='US/Eastern'),
        id='evening_scrape',
        name='Evening rate scrape (7pm EST)',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600,
    )

    scheduler.start()
    print("[SCHEDULER] Started — 7:00 AM and 7:00 PM EST scrape jobs scheduled")
