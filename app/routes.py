from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import schemas
from app.models import Resource
from app.schemas import MessageResponse, UserInfo
from app.auth_decorators import get_current_user, require_permission
from app.services.permission_service import PermissionService
from app.exceptions import ResourceNotFoundException, FGAOperationException
from config import get_db

router = APIRouter(
    prefix="/api/v1",
)

@router.get("/health", response_model=schemas.HealthResponse)
async def health_check():
    return {"status": "healthy"}

@router.get("/resources", response_model=List[schemas.ResourceResponse])
async def list_resources(
        user_email: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    resources = db.query(Resource).all()
    
    if not resources:
        return []
    
    # バッチチェックで効率化
    resource_uuids = [str(r.uuid) for r in resources]
    try:
        permissions = await PermissionService.batch_check_permissions(
            user_email, resource_uuids, "viewer"
        )
    except Exception:
        # フォールバック: 個別チェック
        permissions = []
        for uuid in resource_uuids:
            try:
                allowed = await PermissionService.check_permission(user_email, uuid, "viewer")
                permissions.append(allowed)
            except Exception:
                permissions.append(False)
    
    accessible_resources = [
        resource for resource, allowed in zip(resources, permissions) if allowed
    ]
    
    return accessible_resources


@router.post("/resources", response_model=schemas.ResourceResponse)
async def create_resource(
        resource: schemas.ResourceCreate,
        user_email: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    new_resource = Resource(name=resource.name, owner=user_email)
    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)

    try:
        await PermissionService.grant_permission(
            user_email, str(new_resource.uuid), "owner"
        )
    except FGAOperationException as e:
        # ロールバック
        db.delete(new_resource)
        db.commit()
        raise e

    return new_resource


@router.get("/resources/{resource_uuid}", response_model=schemas.ResourceResponse)
@require_permission("viewer")
async def get_resource(
    resource_uuid: str,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise ResourceNotFoundException(resource_uuid)
    
    return resource


@router.post("/resources/{resource_uuid}/share", response_model=schemas.ShareResponse)
@require_permission("owner")
async def share_resource(
    resource_uuid: str,
    share_request: schemas.ShareRequest,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise ResourceNotFoundException(resource_uuid)
    
    await PermissionService.grant_permission(
        share_request.user_email, 
        str(resource.uuid), 
        share_request.relation
    )

    return schemas.ShareResponse(
        message="Resource shared successfully",
        resource_uuid=resource_uuid,
        shared_with=share_request.user_email,
        relation=share_request.relation
    )


@router.delete("/resources/{resource_uuid}", response_model=schemas.MessageResponse)
@require_permission("owner")
async def delete_resource(
    resource_uuid: str,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise ResourceNotFoundException(resource_uuid)

    db.delete(resource)
    db.commit()

    return MessageResponse(
        message="Resource deleted successfully"
    )


@router.get("/users/me", response_model=schemas.UserInfo)
async def get_current_user_info(
    user_email: str = Depends(get_current_user)
):
    return UserInfo(
        email=user_email,
        name=user_email.split("@")[0].title()
    )