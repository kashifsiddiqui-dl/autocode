"""Export endpoints — generate and download PDF/CSV/JSON/HL7 exports."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, status
from fastapi.responses import FileResponse

from app.core.dependencies import AuthUser, DBSession
from app.core.exceptions import NotFoundError
from app.schemas.export import ExportFormat, ExportRequest, ExportResponse
from app.services.audit_service import AuditService
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)

router = APIRouter()

_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "json": "application/json",
    "hl7": "application/fhir+json",
}


@router.post("", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    body: ExportRequest,
    user: AuthUser,
    db: DBSession,
    request: Request,
):
    """Generate an export for a coding session."""
    svc = ExportService(db)

    export = await svc.create_export(
        tenant_id=user.tenant_id,
        user_id=user.id,
        session_id=body.session_id,
        format=body.format,
    )

    include_reasoning = True
    include_clinical_notes = True
    if body.options:
        include_reasoning = body.options.include_reasoning
        include_clinical_notes = body.options.include_clinical_notes

    export = await svc.generate_export(
        export_id=export.id,
        tenant_id=user.tenant_id,
        include_reasoning=include_reasoning,
        include_clinical_notes=include_clinical_notes,
    )

    audit = AuditService(db)
    await audit.log_action(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="export.created",
        resource_type="Export",
        resource_id=str(export.id),
        details={
            "session_id": str(body.session_id),
            "format": body.format.value,
            "file_size": export.file_size,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return ExportResponse.model_validate(export)


@router.get("/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    user: AuthUser,
    db: DBSession,
    request: Request,
):
    """Download a generated export file."""
    svc = ExportService(db)
    export = await svc.get_export(export_id, user.tenant_id)

    if export is None:
        raise NotFoundError(f"Export {export_id} not found")

    if export.status != "completed" or not export.file_path:
        raise NotFoundError("Export is not ready for download")

    file_path = Path(export.file_path)
    if not file_path.exists():
        raise NotFoundError("Export file no longer exists")

    content_type = _CONTENT_TYPES.get(export.format, "application/octet-stream")
    filename = f"coding-export-{export.session_id}.{export.format}"
    if export.format == "hl7":
        filename = f"coding-export-{export.session_id}.fhir.json"

    audit = AuditService(db)
    await audit.log_action(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="export.downloaded",
        resource_type="Export",
        resource_id=str(export_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=filename,
    )
