from functools import wraps
from typing import Optional
from fastapi import HTTPException, Depends, Header
from openfga_sdk.client import ClientCheckRequest
from config import fga_client
from app.exceptions import PermissionDeniedException, FGAOperationException, ValidationException

def get_current_user(x_user_email: Optional[str] = Header(default=None)) -> str:
    from config import Config
    return x_user_email or Config.DEFAULT_USER_EMAIL

def require_permission(relation: str):
    """OpenFGA権限チェックのデコレータ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # パラメータからresource_uuidを取得
            resource_uuid = kwargs.get('resource_uuid')
            if not resource_uuid:
                raise ValidationException("Resource UUID required")
            
            # ユーザー情報を取得（実際の実装ではDependsから取得）
            user_email = kwargs.get('user_email') or "alice@example.com"
            
            # OpenFGAで権限チェック
            check_request = ClientCheckRequest(
                user=f"user:{user_email}",
                relation=relation,
                object=f"resource:{resource_uuid}",
            )
            
            try:
                response = await fga_client.check(check_request)
                if not response.allowed:
                    raise PermissionDeniedException()
            except PermissionDeniedException:
                raise
            except Exception as e:
                raise FGAOperationException("check", str(e))
            
            # 権限チェックが通った場合、元の関数を実行
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# 使用例用のヘルパー関数
async def check_resource_permission(user_email: str, resource_uuid: str, relation: str) -> bool:
    """リソース権限チェック関数"""
    check_request = ClientCheckRequest(
        user=f"user:{user_email}",
        relation=relation,
        object=f"resource:{resource_uuid}",
    )
    
    try:
        response = await fga_client.check(check_request)
        return response.allowed
    except Exception:
        return False