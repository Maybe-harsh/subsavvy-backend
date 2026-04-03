from sqlalchemy import Column, String, Float, Date, ForeignKey, JSON, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

# Base class for all models
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    taste_profile = Column(JSON, default=list) # Stores your AI keywords like ["dark fantasy", "sci-fi"]
    created_at = Column(DateTime, default=datetime.utcnow)
    trakt_access_token = Column(String, nullable=True)
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False) # e.g., "Netflix", "Crunchyroll"
    category = Column(String)             # e.g., "Video Streaming"
    affiliate_url = Column(String)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="platform")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform_id = Column(UUID(as_uuid=True), ForeignKey("platforms.id"), nullable=False)
    cost = Column(Float, nullable=False)
    billing_cycle = Column(String, default="Monthly")
    next_billing_date = Column(Date, nullable=False)
    status = Column(String, default="Active")

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    platform = relationship("Platform", back_populates="subscriptions")
    usage_logs = relationship("UsageLog", back_populates="subscription", cascade="all, delete-orphan")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    date_logged = Column(Date, nullable=False)
    minutes_used = Column(Integer, default=0)

    # Relationships
    subscription = relationship("Subscription", back_populates="usage_logs")