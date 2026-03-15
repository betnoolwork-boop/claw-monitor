from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.auth_service import require_auth
from app.services.presets_service import get_presets, create_preset, update_preset, delete_preset, apply_preset

router = APIRouter(prefix='/api/presets', tags=['presets'])


class PresetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    filters: dict = Field(default_factory=dict)
    is_default: bool = False


class PresetCreate(PresetBase):
    pass


class PresetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    filters: Optional[dict] = Field(None)
    is_default: Optional[bool] = Field(None)


class PresetResponse(PresetBase):
    id: str
    created_at: float
    updated_at: float
    owner: str


@router.get('', response_model=List[PresetResponse])
def list_presets(request: Request, _=Depends(require_auth)):
    return get_presets(owner=request.state.user['id'])


@router.post('', response_model=PresetResponse)
def create_new_preset(preset: PresetCreate, request: Request, _=Depends(require_auth)):
    return create_preset(preset.dict(), owner=request.state.user['id'])


@router.put('/{preset_id}', response_model=PresetResponse)
def update_existing_preset(preset_id: str, preset: PresetUpdate, request: Request, _=Depends(require_auth)):
    return update_preset(preset_id, preset.dict(), owner=request.state.user['id'])


@router.delete('/{preset_id}')
def delete_preset_by_id(preset_id: str, request: Request, _=Depends(require_auth)):
    return delete_preset(preset_id, owner=request.state.user['id'])


@router.post('/{preset_id}/apply')
def apply_preset_by_id(preset_id: str, request: Request, _=Depends(require_auth)):
    return apply_preset(preset_id, owner=request.state.user['id'])