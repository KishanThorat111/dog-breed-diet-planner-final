from __future__ import annotations

import uuid
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.diet_service import diet_service
from app.services.pet_service import pet_service
from app.services.report_service import generate_diet_report_pdf

router = APIRouter()


def _safe_report_filename(pet_name: str, plan_id: uuid.UUID) -> str:
    """Build an ASCII-safe filename for Content-Disposition headers."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", pet_name.strip())
    cleaned = cleaned.strip("-") or "pet"
    return f"diet-report-{cleaned}-{plan_id}.pdf"


async def _build_diet_plan_pdf_response(
    plan_id: uuid.UUID,
    expected_pet_id: uuid.UUID | None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Generate and download a PDF diet plan report."""
    plan = await diet_service.get_by_id(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diet plan not found")

    if expected_pet_id is not None and plan.pet_id != expected_pet_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diet plan not found")

    pet = await pet_service.get_by_id(db, plan.pet_id, current_user.id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    pdf_bytes = generate_diet_report_pdf(pet, plan)
    filename = _safe_report_filename(pet.name or "pet", plan.id)
    utf8_filename = quote(filename)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{utf8_filename}",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/diet-plan/{plan_id}/pdf")
async def download_diet_plan_pdf(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    return await _build_diet_plan_pdf_response(plan_id, None, db, current_user)


@router.get("/{pet_id}/diet-plan/{plan_id}/pdf")
async def download_diet_plan_pdf_legacy(
    pet_id: uuid.UUID,
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Backward-compatible route used by older frontend builds."""
    return await _build_diet_plan_pdf_response(plan_id, pet_id, db, current_user)
