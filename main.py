from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db
import models
import crud
import schemas
import auth
import recommendation
from scheduler import task_scheduler
import random
import requests
import os

# --- TMDB AI BRAIN CONFIGURATION ---
# FIX: Moved API key out of source code — load from .env instead
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

TMDB_GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
    10759: "Action & Adventure", 10765: "Sci-Fi & Fantasy",
    10768: "War & Politics", 10762: "Kids", 10766: "Soap",
    10767: "Talk", 10763: "News", 10764: "Reality"
}

def fetch_genres_for_title(title: str):
    """Pings TMDB to find the genres of the movie/show."""
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={title}&language=en-US&page=1"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("results") and len(data["results"]) > 0:
            best_match = data["results"][0]
            genre_ids = best_match.get("genre_ids", [])
            return [TMDB_GENRE_MAP[g_id] for g_id in genre_ids if g_id in TMDB_GENRE_MAP]
    except Exception as e:
        print(f"\n TMDB Error: {e}")
    return []

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Define the lifespan of the app (Startup and Shutdown events)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("\n Syncing Database Tables...")
    models.Base.metadata.create_all(bind=engine)
    print("\n Starting API and Background Scheduler...")
    task_scheduler.start()
    yield  # The application runs here
    # --- SHUTDOWN ---
    print("\n Shutting down API and Background Scheduler...")
    task_scheduler.shutdown()

# Initialize FastAPI with the lifespan
app = FastAPI(
    title="Subscription Tracker API",
    lifespan=lifespan
)

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://subsavvy-frontend-virid.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online"}

# --- SILENCE FAVICON ERROR ---
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Returns an empty dummy response to silence browser favicon requests."""
    return Response(content=b"", media_type="image/x-icon")

# --- AUTHENTICATION ROUTE ---
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticates a user and returns a JWT token."""
    user = crud.get_user_by_email(db, email=form_data.username.lower())
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- USER ROUTES ---
@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new user."""
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Fetches the currently logged-in user's profile."""
    return current_user

# --- SUBSCRIPTION ROUTES ---
@app.post("/users/me/subscriptions/", response_model=schemas.SubscriptionResponse)
def create_subscription_for_user(
    subscription_req: schemas.SubscriptionCreateFrontend,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Adds a new subscription to the currently authenticated user's account."""
    platform = crud.get_or_create_platform(db, platform_name=subscription_req.platform_name)
    db_subscription = schemas.SubscriptionCreate(
        platform_id=platform.id,
        cost=subscription_req.cost,
        billing_cycle=subscription_req.billing_cycle,
        next_billing_date=subscription_req.next_billing_date,
        status="Active"
    )
    return crud.create_user_subscription(db=db, subscription=db_subscription, user_id=current_user.id)

@app.get("/users/me/subscriptions/", response_model=list[schemas.SubscriptionResponse])
def read_subscriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves all active subscriptions for the currently authenticated user."""
    subscriptions = crud.get_user_subscriptions(db, user_id=current_user.id, skip=skip, limit=limit)
    return subscriptions

@app.put("/users/me/subscriptions/{sub_id}", response_model=schemas.SubscriptionResponse)
def update_subscription(
    sub_id: str,
    subscription_req: schemas.SubscriptionCreateFrontend,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Updates a specific subscription."""
    updated_sub = crud.update_user_subscription(db, sub_id, current_user.id, subscription_req)
    if not updated_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return updated_sub

@app.delete("/users/me/subscriptions/{sub_id}")
def delete_subscription(
    sub_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Deletes a specific subscription."""
    success = crud.delete_user_subscription(db, sub_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"detail": "Subscription deleted successfully"}

# --- AI ALERTS ROUTE ---
@app.get("/users/me/alerts")
def get_user_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Triggers the AI engine to analyze the user's data and return smart alerts."""
    alerts = recommendation.generate_alerts_for_user(db=db, user_id=current_user.id)
    return alerts

# --- NETFLIX-STYLE RECOMMENDATION ROUTE ---
@app.get("/recommendations")
def get_recommendations(current_user: models.User = Depends(auth.get_current_user)):
    print(f"\n AI: Fetching Netflix-Style Mix with Providers for {current_user.email}...")
    tastes = getattr(current_user, 'taste_profile', []) or []
    reverse_genre_map = {v: k for k, v in TMDB_GENRE_MAP.items()}
    genre_ids = [reverse_genre_map.get(g) for g in tastes if g in reverse_genre_map]
    genre_str = "|".join(map(str, genre_ids)) if genre_ids else ""

    if genre_ids:
        global_url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&with_genres={genre_str}&sort_by=popularity.desc"
        regional_url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&with_genres={genre_str}&sort_by=popularity.desc&with_origin_country=IN"
    else:
        global_url = f"https://api.themoviedb.org/3/trending/tv/week?api_key={TMDB_API_KEY}"
        regional_url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&sort_by=popularity.desc&with_origin_country=IN"

    try:
        global_data = requests.get(global_url).json().get('results', [])
        regional_data = requests.get(regional_url).json().get('results', [])
        raw_shows = []
        seen_ids = set()
        for show in regional_data:
            if show['id'] not in seen_ids and len(raw_shows) < 3:
                raw_shows.append(show); seen_ids.add(show['id'])
        for show in global_data:
            if show['id'] not in seen_ids and len(raw_shows) < 6:
                raw_shows.append(show); seen_ids.add(show['id'])
        if not raw_shows:
            return []
        random.shuffle(raw_shows)
        results = []
        for show in raw_shows:
            show_genres = show.get('genre_ids', [])
            overlap = len(set(show_genres) & set(genre_ids)) if genre_ids else 0
            match_val = 75 + (overlap * 5) + (show.get('vote_average', 0) * 2)
            display_genre = "Popular"
            if show_genres:
                for g_id in show_genres:
                    if g_id in TMDB_GENRE_MAP:
                        display_genre = TMDB_GENRE_MAP[g_id]; break
            image_path = show.get('backdrop_path') or show.get('poster_path')
            media_type = show.get('media_type', 'tv')
            show_id = show['id']
            trailer_url = None
            try:
                vid_url = f"https://api.themoviedb.org/3/{media_type}/{show_id}/videos?api_key={TMDB_API_KEY}"
                vid_resp = requests.get(vid_url).json()
                yt_videos = [v for v in vid_resp.get('results', []) if v.get('site') == 'YouTube']
                if yt_videos:
                    best_vid = next((v for v in yt_videos if v.get('type') == 'Trailer'), None)
                    if not best_vid: best_vid = next((v for v in yt_videos if v.get('type') == 'Teaser'), None)
                    if not best_vid: best_vid = yt_videos[0]
                    trailer_url = f"https://www.youtube.com/embed/{best_vid.get('key')}?autoplay=1"
            except: pass
            providers = []
            watch_link = None
            try:
                prov_url = f"https://api.themoviedb.org/3/{media_type}/{show_id}/watch/providers?api_key={TMDB_API_KEY}"
                prov_resp = requests.get(prov_url).json()
                in_data = prov_resp.get('results', {}).get('IN', {})
                watch_link = in_data.get('link')
                in_providers = in_data.get('flatrate', [])
                for prov in in_providers[:2]:
                    providers.append({
                        "name": prov.get("provider_name"),
                        "logo": f"https://image.tmdb.org/t/p/w45{prov.get('logo_path')}"
                    })
            except: pass
            results.append({
                "id": show_id, "title": show.get('name', show.get('title', 'Unknown Title')),
                "genre": display_genre, "match": f"{min(99, int(match_val))}% Match",
                "image": f"https://image.tmdb.org/t/p/w780{image_path}" if image_path else "https://images.unsplash.com/photo-1584905066893-7d5c142ba4e1",
                "trailer": trailer_url, "providers": providers, "watch_link": watch_link
            })
        return results
    except Exception as e:
        print(f"\n API Error: {e}")
        return []

# --- USAGE LOGGING ---
@app.post("/usage/", response_model=schemas.UsageLogResponse)
def log_usage(usage: schemas.UsageLogCreate, db: Session = Depends(get_db)):
    """Receives ping from browser extension/app about minutes watched."""
    return crud.log_subscription_usage(db=db, usage=usage)

# --- EXTENSION USAGE ROUTE ---
@app.post("/usage/extension")
def log_usage_from_extension(
    usage_req: schemas.UsageLogExtensionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Receives ping from Chrome Extension and securely logs it to the authenticated user."""
    platform = crud.get_or_create_platform(db, platform_name=usage_req.platform_name)
    title = getattr(usage_req, 'title', None)
    if title and title != "Unknown Title":
        try:
            discovered_genres = fetch_genres_for_title(title)
            if discovered_genres:
                current_tastes = getattr(current_user, 'taste_profile', []) or []
                updated_tastes = list(set(current_tastes + discovered_genres))
                current_user.taste_profile = updated_tastes[-20:]
                db.commit()
                print(f"\n AI Brain: Learned tastes for {current_user.email} from '{title}'")
        except Exception as e:
            print(f"\n TMDB Error: {e}")
    sub = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.platform_id == platform.id
    ).first()
    if sub:
        db_usage = models.UsageLog(
            subscription_id=sub.id,
            date_logged=usage_req.date_logged,
            minutes_used=usage_req.minutes_used
        )
        db.add(db_usage)
        db.commit()
    return {"status": "success", "logged_minutes": usage_req.minutes_used, "title": title}

# FIX: Removed duplicate @app.on_event("startup") — scheduler is already started in lifespan above

@app.delete("/subscriptions/{subscription_id}/logs")
def reset_usage_logs(subscription_id: str, db: Session = Depends(get_db)):
    db.query(models.UsageLog).filter(models.UsageLog.subscription_id == subscription_id).delete()
    db.commit()
    return {"message": "Logs reset successfully"}