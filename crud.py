from sqlalchemy.orm import Session
import models
import schemas
import auth

# --- USER OPERATIONS ---

def get_user_by_email(db: Session, email: str):
    """Retrieve a user by their email address, ensuring case-insensitivity."""
    # Force lowercase for the lookup
    return db.query(models.User).filter(models.User.email == email.lower()).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user and securely hash their password."""
    hashed_password = auth.get_password_hash(user.password) 
    
    db_user = models.User(
        email=user.email.lower(), # <-- Force lowercase before saving
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- PLATFORM OPERATIONS (NEW) ---

def get_or_create_platform(db: Session, platform_name: str):
    """Finds a platform by name, or creates it if it doesn't exist."""
    # .ilike() makes the search case-insensitive (so 'netflix' == 'Netflix')
    platform = db.query(models.Platform).filter(models.Platform.name.ilike(platform_name)).first()
    
    if not platform:
        platform = models.Platform(name=platform_name)
        db.add(platform)
        db.commit()
        db.refresh(platform)
        
    return platform

# --- SUBSCRIPTION OPERATIONS ---

def create_user_subscription(db: Session, subscription: schemas.SubscriptionCreate, user_id: str):
    """Add a new subscription to a specific user's account."""
    db_subscription = models.Subscription(
        **subscription.model_dump(), 
        user_id=user_id
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

def get_user_subscriptions(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    """Get a list of all subscriptions for a specific user."""
    return db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id
    ).offset(skip).limit(limit).all()

# --- USAGE LOGGING ---

def log_subscription_usage(db: Session, usage: schemas.UsageLogCreate):
    """Record how many minutes a user spent on a platform."""
    db_usage = models.UsageLog(**usage.model_dump())
    db.add(db_usage)
    db.commit()
    db.refresh(db_usage)
    return db_usage


# --- UPDATE & DELETE SUBSCRIPTIONS (NEW) ---

def update_user_subscription(db: Session, sub_id: str, user_id: str, sub_update: schemas.SubscriptionCreateFrontend):
    """Updates an existing subscription."""
    # 1. Find the exact subscription
    sub = db.query(models.Subscription).filter(
        models.Subscription.id == sub_id, 
        models.Subscription.user_id == user_id
    ).first()
    
    if not sub:
        return None
        
    # 2. Check if they changed the platform name (get or create the new UUID)
    platform = get_or_create_platform(db, platform_name=sub_update.platform_name)
    
    # 3. Apply the changes
    sub.platform_id = platform.id
    sub.cost = sub_update.cost
    sub.billing_cycle = sub_update.billing_cycle
    sub.next_billing_date = sub_update.next_billing_date
    
    db.commit()
    db.refresh(sub)
    return sub

def delete_user_subscription(db: Session, sub_id: str, user_id: str):
    """Deletes a subscription from the database."""
    sub = db.query(models.Subscription).filter(
        models.Subscription.id == sub_id, 
        models.Subscription.user_id == user_id
    ).first()
    
    if sub:
        db.delete(sub)
        db.commit()
        return True
    return False