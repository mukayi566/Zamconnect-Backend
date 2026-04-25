from typing import Any, Optional

def api_response(success: bool, message: str, data: Any = None, meta: Optional[dict] = None, code: Optional[str] = None):
    response = {
        "success": success,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    if meta is not None:
        response["meta"] = meta
    if not success and code:
        response["code"] = code
        
    return response
