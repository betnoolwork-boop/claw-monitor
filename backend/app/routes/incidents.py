from fastapi import APIRouter, Depends, Request

from app.services.auth_service import require_auth
from app.services.incidents_service import get_incident_detail, get_incident_events, get_incident_summary, get_incident_timeline, get_provider_incidents

router = APIRouter(prefix='/api/incidents', tags=['incidents'])


@router.get('/summary')
def incidents_summary(_: Request, __=Depends(require_auth)):
    return get_incident_summary()


@router.get('/events')
def incidents_events(_: Request, __=Depends(require_auth)):
    return {'items': get_incident_events()}


@router.get('/providers')
def incidents_providers(_: Request, __=Depends(require_auth)):
    return get_provider_incidents()


@router.get('/timeline')
def incidents_timeline(_: Request, __=Depends(require_auth)):
    return get_incident_timeline()


@router.get('/detail/{event_id:path}')
def incidents_detail(event_id: str, _: Request, __=Depends(require_auth)):
    return get_incident_detail(event_id)
