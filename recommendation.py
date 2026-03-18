from sqlalchemy.orm import Session
import models

# --- COMMERCIAL GRADE CATALOG ---
# Using strict sets for deterministic, high-speed matching instead of brittle NLP
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
    # Normalize tastes to lowercase for strict matching
    user_tags = set([t.lower() for t in taste_list]) if taste_list else {"drama", "comedy", "action"}
        
    subs = db.query(models.Subscription).filter(models.Subscription.user_id == user_id).all()
    
    if not subs:
        return [{"platform": "Welcome", "message": "Add your first subscription below so our AI can start optimizing your spending!", "type": "info"}]

    active_subscriptions = {}
    for sub in subs:
        platform = db.query(models.Platform).filter(models.Platform.id == sub.platform_id).first()
        platform_name = platform.name if platform else "Unknown"
        logs = db.query(models.UsageLog).filter(models.UsageLog.subscription_id == sub.id).all()
        
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
            
            # 1. Score all platforms the user DOES NOT currently have
            for cat in PLATFORM_CATALOGS:
                if cat["platform"] in active_subscriptions:
                    continue 
                
                # Calculate exact overlap score
                overlap = len(user_tags & cat["tags"])
                if overlap > highest_score:
                    highest_score = overlap
                    best_alt = cat

            # 2. Dynamic Commercial Messaging
            if best_alt and highest_score > 0:
                cost_diff = current_cost - best_alt["cost"]
                primary_taste = taste_list[0] if taste_list else "your tastes"
                
                if cost_diff > 0:
                    # Alternative is Cheaper
                    msg = f"You aren't using {platform_name} ({minutes} mins). Switch to {best_alt['platform']} for better '{primary_taste}' content and save ₹{cost_diff:.0f}/mo."
                elif cost_diff == 0:
                    # Alternative is Same Price
                    msg = f"You aren't using {platform_name} ({minutes} mins). Switch to {best_alt['platform']} for the exact same price to get content that actually matches your love for '{primary_taste}'."
                else:
                    # Alternative is More Expensive (Value Upsell)
                    msg = f"You're wasting ₹{current_cost:.0f}/mo on {platform_name} ({minutes} mins). For just ₹{abs(cost_diff):.0f} more, {best_alt['platform']} offers a massive catalog perfectly matched to your '{primary_taste}' DNA."

                alerts.append({
                    "platform": platform_name, "message": msg, "type": "warning",
                    "action_text": f"Explore {best_alt['platform']} ", "action_url": best_alt['url']
                })
            else:
                # Absolute fallback if no other platforms exist or match
                alerts.append({"platform": platform_name, "message": f"You only used {platform_name} for {minutes} mins. Consider cancelling it to save ₹{current_cost:.0f}/mo.", "type": "alert"})
                
        elif current_cost > 0:
            cost_per_minute = current_cost / minutes
            if cost_per_minute > 5.00: 
                alerts.append({"platform": platform_name, "message": f"You're paying a massive ₹{cost_per_minute:.2f} per minute of watch time on {platform_name}! Is it really worth it?", "type": "alert"})

    if not alerts:
        alerts.append({"platform": "Highly Optimized", "message": "Great job! Your subscriptions perfectly match your watch habits. No wasted money detected.", "type": "success"})

    return alerts