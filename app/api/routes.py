import hashlib, secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, require_agency_admin, require_client_membership, require_active_subscription
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.entities import User, Client, Membership, Invitation, BrandProfile, Subscription, ContentItem, UserRole, SubscriptionStatus, ContentStatus
from app.schemas import LoginIn, TokenOut, UserOut, ClientCreate, ClientOut, InvitationAccept, BrandUpdate, BrandOut, ContentGenerateIn, ContentOut
router = APIRouter()

@router.post("/auth/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash): raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(access_token=create_access_token(user.id))

@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)): return user

@router.post("/clients", status_code=201)
async def create_client(payload: ClientCreate, admin: User = Depends(require_agency_admin), db: AsyncSession = Depends(get_db)):
    client = Client(name=payload.name, slug=payload.slug, created_by_user_id=admin.id)
    db.add(client)
    try:
        await db.flush()
        db.add(BrandProfile(client_id=client.id, brand_name=payload.name))
        db.add(Subscription(client_id=client.id, status=SubscriptionStatus.INCOMPLETE))
        token = secrets.token_urlsafe(32)
        db.add(Invitation(client_id=client.id, email=payload.owner_email.lower(), role=UserRole.CLIENT_OWNER, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.now(timezone.utc)+timedelta(hours=settings.invitation_ttl_hours)))
        await db.commit(); await db.refresh(client)
    except IntegrityError:
        await db.rollback(); raise HTTPException(status_code=409, detail="Workspace slug already exists") from None
    # Development only: send this URL by transactional email in production; never expose raw invite tokens in API responses.
    return {"id": client.id, "name": client.name, "slug": client.slug, "status": client.status.value, "invitation_url_dev_only": f"{settings.app_base_url}/accept-invitation?token={quote(token)}"}

@router.get("/clients", response_model=list[ClientOut])
async def list_clients(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.email.lower() in settings.agency_admin_email_set: rows = await db.scalars(select(Client).order_by(Client.created_at.desc()))
    else: rows = await db.scalars(select(Client).join(Membership, Membership.client_id == Client.id).where(Membership.user_id == user.id).order_by(Client.created_at.desc()))
    return list(rows)

@router.post("/invitations/accept", response_model=TokenOut)
async def accept_invitation(payload: InvitationAccept, db: AsyncSession = Depends(get_db)):
    invitation = await db.scalar(select(Invitation).where(Invitation.token_hash == hashlib.sha256(payload.token.encode()).hexdigest()))
    now = datetime.now(timezone.utc)
    if not invitation or invitation.accepted_at or invitation.expires_at < now: raise HTTPException(status_code=400, detail="Invitation is invalid or expired")
    if await db.scalar(select(User).where(User.email == invitation.email)): raise HTTPException(status_code=409, detail="An account already exists for this email; contact workspace support")
    user = User(email=invitation.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user); await db.flush()
    db.add(Membership(client_id=invitation.client_id, user_id=user.id, role=invitation.role)); invitation.accepted_at = now
    await db.commit()
    return TokenOut(access_token=create_access_token(user.id))

@router.get("/clients/{client_id}/brand", response_model=BrandOut)
async def get_brand(client_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await require_client_membership(client_id, user, db)
    brand = await db.get(BrandProfile, client_id)
    if not brand: raise HTTPException(status_code=404, detail="Brand profile not found")
    return brand

@router.put("/clients/{client_id}/brand", response_model=BrandOut)
async def update_brand(client_id: str, payload: BrandUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    membership = await require_client_membership(client_id, user, db)
    if membership.role not in (UserRole.CLIENT_OWNER, UserRole.MARKETER, UserRole.EDITOR): raise HTTPException(status_code=403, detail="Insufficient permissions")
    await require_active_subscription(client_id, db)
    brand = await db.get(BrandProfile, client_id)
    if not brand: brand = BrandProfile(client_id=client_id); db.add(brand)
    brand.brand_name = payload.brand_name; brand.website_url = str(payload.website_url) if payload.website_url else None; brand.audience = payload.audience; brand.tone_of_voice = payload.tone_of_voice; brand.prohibited_claims = payload.prohibited_claims
    await db.commit(); await db.refresh(brand)
    return brand

@router.post("/content/generate", response_model=list[ContentOut], status_code=201)
async def generate_content(payload: ContentGenerateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    membership = await require_client_membership(payload.client_id, user, db)
    if membership.role not in (UserRole.CLIENT_OWNER, UserRole.MARKETER, UserRole.EDITOR): raise HTTPException(status_code=403, detail="Insufficient permissions")
    await require_active_subscription(payload.client_id, db)
    brand = await db.get(BrandProfile, payload.client_id)
    from app.services.ai import generate_drafts
    drafts = await generate_drafts(payload.topic, payload.channel, payload.goal, payload.count, brand)
    items = [ContentItem(client_id=payload.client_id, created_by_user_id=user.id, title=d["title"], channel=payload.channel, body=d["body"], status=ContentStatus.DRAFT, ai_metadata={"provider": d.get("provider", "template")}) for d in drafts]
    db.add_all(items); await db.commit()
    for item in items: await db.refresh(item)
    return items

@router.get("/clients/{client_id}/content", response_model=list[ContentOut])
async def list_content(client_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await require_client_membership(client_id, user, db); await require_active_subscription(client_id, db)
    rows = await db.scalars(select(ContentItem).where(ContentItem.client_id == client_id).order_by(ContentItem.created_at.desc()).limit(100))
    return list(rows)

async def require_client_owner(client_id: str, user: User, db: AsyncSession):
    membership = await require_client_membership(client_id, user, db)
    if membership.role != UserRole.CLIENT_OWNER: raise HTTPException(status_code=403, detail="Workspace owner permission required")

@router.post("/billing/checkout-session")
async def create_checkout_session(client_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await require_client_owner(client_id, user, db)
    if not settings.stripe_secret_key or not settings.stripe_default_price_id: raise HTTPException(status_code=503, detail="Billing is not configured")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    sub = await db.scalar(select(Subscription).where(Subscription.client_id == client_id)); client = await db.get(Client, client_id)
    if not sub or not client: raise HTTPException(status_code=404, detail="Workspace billing record not found")
    if not sub.stripe_customer_id:
        customer = stripe.Customer.create(name=client.name, metadata={"client_id": client_id}); sub.stripe_customer_id = customer.id; await db.commit()
    session = stripe.checkout.Session.create(mode="subscription", customer=sub.stripe_customer_id, line_items=[{"price": settings.stripe_default_price_id, "quantity": 1}], success_url=f"{settings.app_base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}", cancel_url=f"{settings.app_base_url}/billing/cancel", subscription_data={"metadata": {"client_id": client_id}}, metadata={"client_id": client_id})
    return {"checkout_url": session.url}

@router.post("/billing/portal-session")
async def create_portal_session(client_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await require_client_owner(client_id, user, db)
    sub = await db.scalar(select(Subscription).where(Subscription.client_id == client_id))
    if not sub or not sub.stripe_customer_id or not settings.stripe_secret_key: raise HTTPException(status_code=400, detail="Billing customer is not set up yet")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    session = stripe.billing_portal.Session.create(customer=sub.stripe_customer_id, return_url=f"{settings.app_base_url}/settings/billing")
    return {"portal_url": session.url}

@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret: raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    import stripe
    try: event = stripe.Webhook.construct_event(await request.body(), request.headers.get("stripe-signature"), settings.stripe_webhook_secret)
    except Exception: raise HTTPException(status_code=400, detail="Invalid webhook signature or payload") from None
    obj, kind = event["data"]["object"], event["type"]
    if kind == "checkout.session.completed":
        client_id = (obj.get("metadata") or {}).get("client_id")
        sub = await db.scalar(select(Subscription).where(Subscription.client_id == client_id)) if client_id else None
        if sub: sub.stripe_customer_id = obj.get("customer") or sub.stripe_customer_id; sub.stripe_subscription_id = obj.get("subscription") or sub.stripe_subscription_id; await db.commit()
    elif kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        client_id = (obj.get("metadata") or {}).get("client_id")
        sub = await db.scalar(select(Subscription).where(Subscription.client_id == client_id)) if client_id else None
        if not sub and obj.get("id"): sub = await db.scalar(select(Subscription).where(Subscription.stripe_subscription_id == obj["id"]))
        if sub:
            status_map = {"incomplete":SubscriptionStatus.INCOMPLETE,"trialing":SubscriptionStatus.TRIALING,"active":SubscriptionStatus.ACTIVE,"past_due":SubscriptionStatus.PAST_DUE,"canceled":SubscriptionStatus.CANCELED,"unpaid":SubscriptionStatus.UNPAID}
            sub.stripe_subscription_id = obj.get("id"); sub.stripe_customer_id = obj.get("customer") or sub.stripe_customer_id; sub.status = status_map.get(obj.get("status"), SubscriptionStatus.INCOMPLETE)
            price_data = ((obj.get("items") or {}).get("data") or [{}])[0].get("price") or {}; sub.stripe_price_id = price_data.get("id")
            period_end = obj.get("current_period_end"); sub.current_period_end = datetime.fromtimestamp(period_end, timezone.utc) if period_end else None
            await db.commit()
    return {"received": True}
