import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import User, Membership, Subscription, SubscriptionStatus
bearer = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: AsyncSession = Depends(get_db)) -> User:
    if credentials is None: raise HTTPException(status_code=401, detail="Authentication required")
    try: payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError: raise HTTPException(status_code=401, detail="Invalid or expired token") from None
    user = await db.get(User, payload.get("sub", ""))
    if not user or not user.is_active: raise HTTPException(status_code=401, detail="Invalid or inactive user")
    return user

async def require_agency_admin(user: User = Depends(get_current_user)) -> User:
    if user.email.lower() not in settings.agency_admin_email_set: raise HTTPException(status_code=403, detail="Agency administrator access required")
    return user

async def require_client_membership(client_id: str, user: User, db: AsyncSession) -> Membership:
    membership = await db.scalar(select(Membership).where(Membership.client_id == client_id, Membership.user_id == user.id))
    if not membership: raise HTTPException(status_code=404, detail="Workspace not found")
    return membership

async def require_active_subscription(client_id: str, db: AsyncSession) -> Subscription:
    sub = await db.scalar(select(Subscription).where(Subscription.client_id == client_id))
    if not sub or sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING): raise HTTPException(status_code=402, detail="An active subscription is required")
    return sub
