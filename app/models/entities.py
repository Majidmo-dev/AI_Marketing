import enum, uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class UserRole(str, enum.Enum):
    AGENCY_ADMIN = "agency_admin"
    CLIENT_OWNER = "client_owner"
    MARKETER = "marketer"
    EDITOR = "editor"
    APPROVER = "approver"
class ClientStatus(str, enum.Enum): ACTIVE = "active"; SUSPENDED = "suspended"
class SubscriptionStatus(str, enum.Enum):
    INCOMPLETE = "incomplete"; TRIALING = "trialing"; ACTIVE = "active"; PAST_DUE = "past_due"; CANCELED = "canceled"; UNPAID = "unpaid"
class ContentStatus(str, enum.Enum): DRAFT = "draft"; PENDING_APPROVAL = "pending_approval"; APPROVED = "approved"; REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Client(Base):
    __tablename__ = "clients"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(180), index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    status: Mapped[ClientStatus] = mapped_column(Enum(ClientStatus), default=ClientStatus.ACTIVE)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Membership(Base):
    __tablename__ = "client_memberships"
    __table_args__ = (UniqueConstraint("client_id", "user_id", name="uq_client_user"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT_OWNER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT_OWNER)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class BrandProfile(Base):
    __tablename__ = "brand_profiles"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
    brand_name: Mapped[str] = mapped_column(String(180), default="")
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    audience: Mapped[str] = mapped_column(Text, default="")
    tone_of_voice: Mapped[str] = mapped_column(String(500), default="Clear, helpful, professional")
    prohibited_claims: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), unique=True, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class ContentItem(Base):
    __tablename__ = "content_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(250))
    channel: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[ContentStatus] = mapped_column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    ai_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
