"""
Notes — two notebooks:
  MARKET    : general market notes
  PORTFOLIO : notes tied to a specific holding; automatically disappear when
              that company is archived/removed from the portfolio.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.response import success_response
from app.models.portfolio import Note, Company
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class NoteCreate(BaseModel):
    scope: str  # MARKET | PORTFOLIO
    content: str
    company_id: Optional[int] = None


def _serialize(n: Note) -> dict:
    return {
        "id": n.id,
        "scope": n.scope,
        "content": n.content,
        "company_id": n.company_id,
        "company": {
            "symbol": n.company.symbol,
            "name": n.company.company_name,
        } if n.company else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
async def list_notes(scope: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(Note).options(selectinload(Note.company)).order_by(Note.created_at.desc())
    if scope:
        q = q.where(Note.scope == scope)
    notes = (await db.execute(q)).scalars().all()
    # Portfolio notes vanish with their company (archived = removed from portfolio)
    visible = [n for n in notes if n.company_id is None or (n.company and n.company.status != "ARCHIVED")]
    return success_response(data=[_serialize(n) for n in visible])


@router.post("")
async def add_note(data: NoteCreate, db: AsyncSession = Depends(get_db)):
    if data.scope == "PORTFOLIO" and not data.company_id:
        raise HTTPException(422, "company_id is required for PORTFOLIO notes")
    if data.company_id:
        c = (await db.execute(select(Company).where(Company.id == data.company_id))).scalar_one_or_none()
        if not c:
            raise HTTPException(404, "Company not found")
    n = Note(scope=data.scope, content=data.content.strip(), company_id=data.company_id)
    db.add(n)
    await db.commit()
    await db.refresh(n, ["company"])
    return success_response(data=_serialize(n), message="Note added.")


@router.delete("/{note_id}")
async def delete_note(note_id: int, db: AsyncSession = Depends(get_db)):
    n = (await db.execute(select(Note).where(Note.id == note_id))).scalar_one_or_none()
    if not n:
        raise HTTPException(404, "Note not found")
    await db.delete(n)
    await db.commit()
    return success_response(message="Note deleted.")
