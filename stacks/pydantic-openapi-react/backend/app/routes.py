"""Route signatures. Together with the models, these *are* the contract."""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.errors import ApiError
from app.models import (
    ErrorOut,
    Modality,
    Report,
    ReportDraft,
    ReportIn,
    Study,
    StudyStatus,
)
from app import store

router = APIRouter()

# GOTCHA #5 — without these declarations the error branch on the TS side is
# untyped. Declaring the model makes `error.code` / `error.message` real.
NOT_FOUND = {404: {"model": ErrorOut, "description": "No such study."}}
CONFLICT = {409: {"model": ErrorOut, "description": "Study is already reported."}}


@router.get("/studies", response_model=list[Study], tags=["studies"])
def list_studies(
    modality: Modality | None = Query(
        default=None, description="Filter by imaging modality."
    ),
) -> list[Study]:
    """List studies, optionally filtered by modality.

    The `modality` query param is a `str, Enum`, so the generated TS type is a
    literal union — passing `"PET"` from the frontend is a compile error.
    """
    rows = list(store.studies.values())
    if modality is not None:
        rows = [s for s in rows if s.modality is modality]
    return rows


@router.get(
    "/studies/{study_id}",
    response_model=Study,
    responses=NOT_FOUND,
    tags=["studies"],
)
def get_study(study_id: str) -> Study:
    study = store.studies.get(study_id)
    if study is None:
        raise ApiError(404, "study_not_found", f"No study with id {study_id!r}.")
    return study


@router.post(
    "/studies/{study_id}/report",
    response_model=Report,
    responses={**NOT_FOUND, **CONFLICT},
    status_code=201,
    tags=["reports"],
)
def create_report(study_id: str, body: ReportIn) -> Report:
    """Attach a report to a study.

    `body` is a Pydantic model, so the TS call site's `body:` argument is
    checked field by field against it.
    """
    study = store.studies.get(study_id)
    if study is None:
        raise ApiError(404, "study_not_found", f"No study with id {study_id!r}.")
    if study_id in store.reports:
        raise ApiError(409, "already_reported", f"Study {study_id} already has a report.")

    report = Report(
        study_id=study_id,
        findings=body.findings,
        impression=body.impression,
        critical=body.critical,
        created_at=datetime.now(tz=timezone.utc),
    )
    store.reports[study_id] = report
    store.studies[study_id] = study.model_copy(
        update={"status": StudyStatus.REPORTED}
    )
    return report


@router.put(
    "/studies/{study_id}/report/draft",
    response_model=ReportDraft,
    responses=NOT_FOUND,
    tags=["reports"],
)
def save_draft(study_id: str, body: ReportDraft) -> ReportDraft:
    """Autosave a partially-filled report and echo back what was stored.

    The same model on the way in and on the way out — see GOTCHA #1 in
    `models.py` for why that combination is what splits the schema.
    """
    if study_id not in store.studies:
        raise ApiError(404, "study_not_found", f"No study with id {study_id!r}.")
    store.drafts[study_id] = body
    return body


@router.get(
    "/studies/{study_id}/report",
    response_model=Report,
    responses=NOT_FOUND,
    tags=["reports"],
)
def get_report(study_id: str) -> Report:
    report = store.reports.get(study_id)
    if report is None:
        raise ApiError(404, "report_not_found", f"No report for study {study_id!r}.")
    return report


@router.post("/reset", response_model=list[Study], tags=["demo"])
def reset_demo() -> list[Study]:
    """Restore seed data so the demo can be replayed."""
    store.reset()
    return list(store.studies.values())
