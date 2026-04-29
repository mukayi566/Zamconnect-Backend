from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.token_service import decode_token
from app.config.settings import settings
from app.models.enums import UserRole

security = HTTPBearer()

async def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)):
    token = auth.credentials
    try:
        payload = decode_token(token, settings.JWT_ACCESS_SECRET)
        
        if not payload:
            print("Token decoding failed: Payload is None")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        if payload.get("type") != "access":
            print(f"Token type mismatch: Expected 'access', got '{payload.get('type')}'")
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        return payload
    except Exception as e:
        if not isinstance(e, HTTPException):
            print(f"Auth Middleware Error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        raise e

def role_required(allowed_roles: list[UserRole]):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Role not permitted")
        return user
    return role_checker
