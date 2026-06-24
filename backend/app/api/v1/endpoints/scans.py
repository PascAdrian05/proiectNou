from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.user import User
from app.models.website import Website
from app.schemas.scan import ScanJobResponse, ScanRequest, ScanRunRead
from app.tasks.scan_tasks import run_full_scan


router = APIRouter()


@router.post("/enqueue", response_model=ScanJobResponse)
def enqueue_scan(
    payload: ScanRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScanJobResponse:
    website = session.exec(
        select(Website).where(Website.id == payload.website_id, Website.tenant_id == current_user.tenant_id)
    ).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    scan_run = ScanRun(tenant_id=current_user.tenant_id, website_id=website.id, status="pending")
    session.add(scan_run)
    session.commit()
    session.refresh(scan_run)

    task = run_full_scan.delay(str(scan_run.id), str(website.id), website.url, website.domain, str(current_user.tenant_id))
    scan_run.celery_task_id = task.id
    session.add(scan_run)
    session.commit()

    return ScanJobResponse(task_id=task.id, scan_run_id=scan_run.id)


@router.get("/runs", response_model=list[ScanRunRead])
def list_scan_runs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ScanRunRead]:
    runs = session.exec(select(ScanRun).where(ScanRun.tenant_id == current_user.tenant_id)).all()
    return [ScanRunRead.model_validate(item) for item in runs]


@router.delete("/history")
def delete_scan_history(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    scan_runs = session.exec(select(ScanRun).where(ScanRun.tenant_id == current_user.tenant_id)).all()
    deleted_count = 0

    for scan_run in scan_runs:
        finding_ids = session.exec(select(Finding.id).where(Finding.scan_run_id == scan_run.id)).all()
        if finding_ids:
            session.exec(delete(Alert).where(Alert.finding_id.in_(finding_ids)))
        session.exec(delete(Finding).where(Finding.scan_run_id == scan_run.id))
        session.delete(scan_run)
        deleted_count += 1

    session.commit()
    return {"deleted_scan_runs": deleted_count}


@router.delete("/{scan_run_id}")
def delete_scan_run(
    scan_run_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    scan_run = session.exec(select(ScanRun).where(ScanRun.id == scan_run_id, ScanRun.tenant_id == current_user.tenant_id)).first()
    if not scan_run:
        raise HTTPException(status_code=404, detail="Scan run not found")

    finding_ids = session.exec(select(Finding.id).where(Finding.scan_run_id == scan_run.id)).all()
    if finding_ids:
        session.exec(delete(Alert).where(Alert.finding_id.in_(finding_ids)))
    session.exec(delete(Finding).where(Finding.scan_run_id == scan_run.id))
    session.delete(scan_run)
    session.commit()
    return {"status": "deleted"}
