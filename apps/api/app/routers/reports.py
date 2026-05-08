from __future__ import annotations

import uuid

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


@router.get("/diet-plan/{plan_id}/pdf")
async def download_diet_plan_pdf(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Generate and download a PDF diet plan report."""
    plan = await diet_service.get_by_id(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diet plan not found")

    pet = await pet_service.get_by_id(db, plan.pet_id, current_user.id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    pdf_bytes = generate_diet_report_pdf(pet, plan)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="diet-report-{pet.name}-{plan.id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
