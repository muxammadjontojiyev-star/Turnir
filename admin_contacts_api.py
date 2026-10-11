"""
admin_contacts_api.py — mas'ul adminlar kontakti (APIRouter, 2026-10-11).
Mantiq: admin_contacts.py.

  GET /admins/contacts?mode=league|cl|el|div|wc
"""

from fastapi import APIRouter, Depends, HTTPException

from api import get_authenticated_user

router = APIRouter()


@router.get("/admins/contacts")
def admins_contacts(mode: str, user: dict = Depends(get_authenticated_user)):
    from admin_contacts import get_admin_contacts
    contacts = get_admin_contacts(mode, user["id"])
    if contacts is None:
        raise HTTPException(status_code=400, detail="bad_mode")
    return {"mode": mode, "admins": contacts}
