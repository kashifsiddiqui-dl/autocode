"""Patient service — CRUD operations for patient records.

TODO: Implement once endpoint layer is wired.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientService:
    """Tenant-scoped patient CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PatientCreate,
    ) -> Patient:
        """Create a new patient record.

        TODO: Add duplicate-MRN detection within tenant scope.
        """
        patient = Patient(
            tenant_id=tenant_id,
            mrn=data.mrn,
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            demographics=data.demographics,
            created_by=user_id,
        )
        self._session.add(patient)
        await self._session.flush()
        return patient

    async def get(
        self,
        patient_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Patient | None:
        """Fetch a single patient by ID within a tenant."""
        stmt = select(Patient).where(
            Patient.id == patient_id,
            Patient.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Patient], int]:
        """List patients with optional name/MRN search and pagination.

        TODO: Add full-text search index for better performance.
        """
        base = select(Patient).where(Patient.tenant_id == tenant_id)

        if search:
            like = f"%{search}%"
            base = base.where(
                Patient.mrn.ilike(like)
                | Patient.first_name.ilike(like)
                | Patient.last_name.ilike(like)
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * size
        rows_stmt = base.order_by(Patient.last_name, Patient.first_name).offset(offset).limit(size)
        result = await self._session.execute(rows_stmt)
        patients = list(result.scalars().all())

        return patients, total

    async def update(
        self,
        patient_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: PatientUpdate,
    ) -> Patient | None:
        """Update an existing patient record.

        TODO: Emit audit log on change.
        """
        patient = await self.get(patient_id, tenant_id)
        if patient is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)

        await self._session.flush()
        return patient

    async def delete(
        self,
        patient_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Soft-delete or hard-delete a patient.

        TODO: Decide on soft-delete strategy (is_active flag vs actual delete).
        """
        patient = await self.get(patient_id, tenant_id)
        if patient is None:
            return False

        await self._session.delete(patient)
        await self._session.flush()
        return True
