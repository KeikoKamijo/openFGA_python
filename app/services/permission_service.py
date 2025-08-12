from typing import Optional, List
from openfga_sdk.client import ClientCheckRequest, ClientWriteRequest, ClientTuple
from openfga_sdk.client.models import BatchCheckRequest, BatchCheckItem
from config import fga_client
from app.exceptions import FGAOperationException


class PermissionService:
    """OpenFGAの権限管理を扱うサービスクラス"""
    
    @staticmethod
    async def check_permission(user_email: str, resource_uuid: str, relation: str) -> bool:
        """単一リソースの権限チェック"""
        check_request = ClientCheckRequest(
            user=f"user:{user_email}",
            relation=relation,
            object=f"resource:{resource_uuid}",
        )
        
        try:
            response = await fga_client.check(check_request)
            return response.allowed
        except Exception as e:
            raise FGAOperationException("check", str(e))
    
    @staticmethod
    async def grant_permission(user_email: str, resource_uuid: str, relation: str) -> None:
        """権限の付与"""
        write_request = ClientWriteRequest(
            writes=[
                ClientTuple(
                    user=f"user:{user_email}",
                    relation=relation,
                    object=f"resource:{resource_uuid}",
                )
            ]
        )
        
        try:
            await fga_client.write(write_request)
        except Exception as e:
            raise FGAOperationException("write", str(e))
    
    @staticmethod
    async def revoke_permission(user_email: str, resource_uuid: str, relation: str) -> None:
        """権限の剥奪"""
        write_request = ClientWriteRequest(
            deletes=[
                ClientTuple(
                    user=f"user:{user_email}",
                    relation=relation,
                    object=f"resource:{resource_uuid}",
                )
            ]
        )
        
        try:
            await fga_client.write(write_request)
        except Exception as e:
            raise FGAOperationException("delete", str(e))
    
    @staticmethod
    async def batch_check_permissions(
        user_email: str, 
        resource_uuids: List[str], 
        relation: str
    ) -> List[bool]:
        """複数リソースの権限を一括チェック"""
        batch_items = [
            BatchCheckItem(
                user=f"user:{user_email}",
                relation=relation,
                object=f"resource:{uuid}"
            )
            for uuid in resource_uuids
        ]
        
        batch_request = BatchCheckRequest(items=batch_items)
        
        try:
            response = await fga_client.batch_check(batch_request)
            return [item.allowed for item in response.result]
        except Exception as e:
            raise FGAOperationException("batch_check", str(e))