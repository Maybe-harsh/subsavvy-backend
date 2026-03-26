from sqlalchemy.orm import Session
from datetime import date, timedelta
import models

# --- COMMERCIAL GRADE CATALOG ---
PLATFORM_CATALOGS = [
    {"platform": "Netflix", "cost": 199.00, "url": "https://www.netflix.com/in/", "tags": {"drama", "thriller", "comedy", "sci-fi", "documentary", "romance", "international", "action", "crime"}},
    {"platform": "Prime Video", "cost": 299.00, "url": "https://www.primevideo.com/?tag=subsavyy-21", "tags": {"action", "superhero", "thriller", "comedy", "drama", "sci-fi", "regional", "family"}},
    {"platform": "Disney+ Hotstar", "cost": 299.00, "url": "https://www.hotstar.com/in?ref=subsavyy", "tags": {"cricket", "marvel", "disney", "bollywood", "drama", "regional", "sports", "kids", "family", "action"}},
    {"platform": "Jio Cinema", "cost": 29.00, "url": "https://www.jiocinema.com/?ref=subsavyy", "tags": {"ipl", "cricket", "hbo", "english", "bollywood", "regional", "comedy", "reality"}},
    {"platform": "Sony Liv", "cost": 299.00, "url": "https://www.sonyliv.com/?ref=subsavyy", "tags": {"sports", "wwe", "original series", "drama", "thriller", "regional", "crime", "action"}},
    {"platform": "ZEE5", "cost": 299.00, "url": "https://www.zee5.com/?ref=subsavyy", "tags": {"bollywood", "regional movies", "daily soaps", "drama", "comedy", "crime"}},
    {"platform": "Crunchyroll", "cost": 79.00, "url": "https://www.crunchyroll.com/?ref=subsavyy", "tags": {"anime", "manga", "japanese", "animation", "shounen"}},
    {"platform": "Discovery+", "cost": 199.00, "url": "https://www.discoveryplus.in/", "tags": {"documentary", "reality", "nature", "science", "history", "survival"}}
]

def generate_alerts_for_user(db: Session, user_id: str):
    """Analyzes real user subscriptions and usage to generate value-driven AI alerts."""

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: return []

    taste_list = getattr(user, 'taste_profile', [])
    user_tags = set([t.lower() for t in taste_list]) if taste_list else {"drama", "comedy", "action"}

    subs = db.query(models.Subscription).filter(models.Subscription.user_id == user_id).all()

    if not subs:
        return [{"platform": "Welcome", "message": "Add your first subscription below so our AI can start optimizing your spending!", "type": "info"}]

    # FIX: Rolling 30-day window (prevents the "1st of the month" false alarm bug)
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    active_subscriptions = {}
    for sub in subs:
        platform = db.query(models.Platform).filter(models.Platform.id == sub.platform_id).first()
        platform_name = platform.name if platform else "Unknown"

        # Look at the last 30 days of actual behavior
        logs = db.query(models.UsageLog).filter(
            models.UsageLog.subscription_id == sub.id,
            models.UsageLog.date_logged >= thirty_days_ago
        ).all()

        is_yearly = getattr(sub, 'billing_cycle', 'monthly').lower() == 'yearly'
        actual_monthly_cost = sub.cost / 12 if is_yearly else sub.cost

        active_subscriptions[platform_name] = {
            "monthly_cost": actual_monthly_cost,
            "minutes_used": sum(log.minutes_used for log in logs)
        }

    alerts = []

    for platform_name, details in active_subscriptions.items():
        minutes = details["minutes_used"]
        current_cost = details["monthly_cost"]

        if minutes < 60:
            best_alt = None
            highest_score = 0

            for cat in PLATFORM_CATALOGS:
                # Case-insensitive check to prevent mismatch errors
                if cat["platform"].lower() in [p.lower() for p in active_subscriptions.keys()]:
                    continue

                overlap = len(user_tags & cat["tags"])
                if overlap > highest_score:
                    highest_score = overlap
                    best_alt = cat

            if best_alt and highest_score > 0:
                cost_diff = current_cost - best_alt["cost"]
                
                # Dynamic text formatting to ensure proper grammar
                primary_taste = f"love for {taste_list[0].title()}" if taste_list else "viewing preferences"

                if cost_diff > 0:
                    msg = f"You aren't using {platform_name} enough ({minutes} mins last 30 days). Switch to {best_alt['platform']} to match your {primary_taste} and save ₹{cost_diff:.0f}/mo."
                elif cost_diff == 0:
                    msg = f"You aren't using {platform_name} enough ({minutes} mins last 30 days). Switch to {best_alt['platform']} for the exact same price to get content that matches your {primary_taste}."
                else:
                    msg = f"You're wasting ₹{current_cost:.0f}/mo on {platform_name} ({minutes} mins last 30 days). For just ₹{abs(cost_diff):.0f} more, {best_alt['platform']} offers a massive catalog matched to your {primary_taste}."

                alerts.append({
                    "platform": platform_name, "message": msg, "type": "warning",
                    "action_text": f"Explore {best_alt['platform']} ", "action_url": best_alt['url']
                })
            else:
                alerts.append({"platform": platform_name, "message": f"You only used {platform_name} for {minutes} mins over the last 30 days. Consider cancelling it to save ₹{current_cost:.0f}/mo.", "type": "alert"})

        elif current_cost > 0:
            # Failsafe against division by zero (though minutes < 60 catches 0, it's a good practice)
            if minutes > 0:
                cost_per_minute = current_cost / minutes
                if cost_per_minute > 5.00:
                    alerts.append({"platform": platform_name, "message": f"You're paying ₹{cost_per_minute:.2f} per minute of watch time on {platform_name} right now! Is it really worth it?", "type": "alert"})

    if not alerts:
        alerts.append({"platform": "Highly Optimized", "message": "Great job! Your subscriptions perfectly match your watch habits over the last 30 days. No wasted money detected.", "type": "success"})

    return alerts