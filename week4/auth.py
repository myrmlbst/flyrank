import os

import httpx
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bearer_scheme = HTTPBearer(auto_error=False)


class Credentials(BaseModel):
    email: str
    password: str


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        response = supabase.auth.get_user(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if response is None or response.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return response.user


def revoke_token(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> None:
    """Revoke the caller's specific access token server-side.

    supabase.auth.sign_out() only clears whatever session is set on the
    Client instance -- and the shared `supabase` client here never has one,
    since get_current_user verifies tokens via get_user(token) rather than
    set_session(). Calling the GoTrue REST endpoint directly with the
    caller's own token is what actually invalidates their session.
    """
    try:
        httpx.post(
            f"{SUPABASE_URL}/auth/v1/logout",
            params={"scope": "local"},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {creds.credentials}"},
            timeout=5,
        )
    except httpx.HTTPError:
        pass
