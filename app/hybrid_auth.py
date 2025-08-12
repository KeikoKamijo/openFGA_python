from functools import wraps
from fastapi import HTTPException, Header
from openfga_sdk.client import ClientCheckRequest
from config import fga_client

# RBAC定義
ROLE_PERMISSIONS = {
    "admin": ["create", "read", "update", "delete"],
    "editor": ["create", "read", "update"], 
    "viewer": ["read"],
    "guest": []
}

def get_user_roles(user_email: str) -> list[str]:
    """ユーザーのロールを取得（実際はJWTやDBから）"""
    role_mapping = {
        "alice@example.com": ["admin"],
        "bob@example.com": ["viewer"], 
        "charlie@example.com": ["guest"]
    }
    return role_mapping.get(user_email, ["guest"])

def has_role_permission(user_email: str, action: str) -> bool:
    """RBAC: ロールベースの権限チェック"""
    user_roles = get_user_roles(user_email)
    for role in user_roles:
        if action in ROLE_PERMISSIONS.get(role, []):
            return True
    return False

async def has_resource_permission(user_email: str, resource_uuid: str, relation: str) -> bool:
    """ReBAC: リソース個別の権限チェック"""
    check_request = ClientCheckRequest(
        user=f"user:{user_email}",
        relation=relation,
        object=f"resource:{resource_uuid}",
    )
    try:
        response = await fga_client.check(check_request)
        return response.allowed
    except:
        return False

def require_permission(action: str, resource_relation: str = None):
    """ハイブリッド権限チェックのデコレータ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_email = kwargs.get('user_email', 'anonymous')
            resource_uuid = kwargs.get('resource_uuid')
            
            # 1. まずRBACでチェック（デフォルト権限）
            if has_role_permission(user_email, action):
                return await func(*args, **kwargs)
            
            # 2. RBACで権限がない場合、ReBACでチェック（個別権限）
            if resource_uuid and resource_relation:
                if await has_resource_permission(user_email, resource_uuid, resource_relation):
                    return await func(*args, **kwargs)
            
            # 3. どちらも通らない場合は拒否
            raise HTTPException(status_code=403, detail="Access denied")
        
        return wrapper
    return decorator