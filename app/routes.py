from fastapi import APIRouter, Depends, HTTPException
from openfga_sdk.client.models import ClientTuple, ClientWriteRequest
from openfga_sdk.client import ClientCheckRequest
from sqlalchemy.orm import Session
from app import schemas
from app.models import Resource
from app.schemas import MessageResponse, UserInfo
from app.auth_decorators import get_current_user, require_permission, check_resource_permission
from config import get_db, fga_client

router = APIRouter(
    prefix="/api/v1",
)

@router.get("/health", response_model=schemas.HealthResponse)
async def health_check():
    return {"status": "healthy"}

@router.get("/resources", response_model=list[schemas.ResourceResponse])
async def list_resources(
        user_email: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    resources = db.query(Resource).all()

    accessible_resources = []
    for resource in resources:
        if await check_resource_permission(user_email, str(resource.uuid), "viewer"):
            accessible_resources.append(resource)

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

    write_request = ClientWriteRequest(
    writes=[
        ClientTuple(
            user=f"user:{user_email}",
            relation="owner",
            object=f"resource:{new_resource.uuid}",
        )
    ]
)
    try:
        await fga_client.write(write_request)
    except Exception as e:
        print(f"Error writing FGA tuple for resource {new_resource.uuid}: {e}")

        db.delete(new_resource)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to set permissions: {str(e)}")

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
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return resource


@router.post("/resources/{resource_uuid}/share", response_model=schemas.ShareResponse)
async def share_resource(
    resource_uuid: str,
    share_request: schemas.ShareRequest,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    check_request = ClientCheckRequest(
        user=f"user:{user_email}",
        relation="owner",  # 'owner' でチェック
        object=f"resource:{resource.uuid}",
    )
    response = await fga_client.check(check_request)
    if not response.allowed:
        raise HTTPException(status_code=403, detail="Access denied")
    write_request = ClientWriteRequest(
        writes=[
            ClientTuple(
                user=f"user:{share_request.user_email}",
                relation=share_request.relation,  # 'viewer' など
                object=f"resource:{resource.uuid}",
            )
        ]
    )
    try:
        await fga_client.write(write_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share resource: {str(e)}")

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
        raise HTTPException(status_code=404, detail="Resource not found")

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