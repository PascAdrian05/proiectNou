from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.core.security import create_access_token
from app.models.oauth_account import OAuthAccount
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.services.oauth_service import build_oauth


router = APIRouter()


@router.get("/{provider}/start")
async def oauth_start(provider: str, request: Request):
	oauth = build_oauth()
	client = oauth.create_client(provider)
	if not client:
		raise HTTPException(status_code=400, detail=f"Provider {provider} is not configured")
	redirect_uri = request.url_for("oauth_callback", provider=provider)
	return await client.authorize_redirect(request, str(redirect_uri))


@router.get("/{provider}/callback", name="oauth_callback")
async def oauth_callback(provider: str, request: Request):
	oauth = build_oauth()
	client = oauth.create_client(provider)
	if not client:
		raise HTTPException(status_code=400, detail=f"Provider {provider} is not configured")

	token = await client.authorize_access_token(request)
	email: str | None = None
	provider_user_id: str | None = None

	if provider == "google":
		user_info = token.get("userinfo") or await client.userinfo(token=token)
		email = user_info.get("email")
		provider_user_id = user_info.get("sub")
	elif provider == "facebook":
		profile = await client.get("me?fields=id,name,email", token=token)
		user_info = profile.json()
		email = user_info.get("email")
		provider_user_id = user_info.get("id")

	if not email or not provider_user_id:
		raise HTTPException(status_code=400, detail="Provider did not return required identity fields")

	with Session(engine) as session:
		linked = session.exec(
			select(OAuthAccount).where(
				OAuthAccount.provider == provider,
				OAuthAccount.provider_user_id == provider_user_id,
			)
		).first()

		user = None
		if linked:
			user = session.get(User, linked.user_id)

		if not user:
			user = session.exec(select(User).where(User.email == email)).first()

		if not user:
			tenant = Tenant(name=f"{email.split('@')[0]} tenant")
			session.add(tenant)
			session.flush()
			user = User(
				tenant_id=tenant.id,
				email=email,
				role="owner",
				hashed_password="oauth-account",
				is_active=True,
			)
			session.add(user)
			session.add(Subscription(tenant_id=tenant.id, plan="free", status="active"))
			session.flush()

		if not linked:
			session.add(
				OAuthAccount(
					user_id=user.id,
					provider=provider,
					provider_user_id=provider_user_id,
					email=email,
				)
			)

		session.commit()
		session.refresh(user)

	jwt_token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
	redirect_target = f"{settings.frontend_url}/?token={quote(jwt_token)}"
	return RedirectResponse(url=redirect_target, status_code=302)
