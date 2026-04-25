from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.token_service import decode_token
from app.config.settings import settings
from app.models.enums import UserRole

security = HTTPBearer()

async def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)):
    token = auth.credentials
    payload = decode_token(token, settings.JWT_ACCESS_SECRET)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
        
    return payload

def role_required(allowed_roles: list[UserRole]):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Role not permitted")
        return user
    return role_checker
