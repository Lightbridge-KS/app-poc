"""In-memory store. No database — this is a PoC about the type pipeline."""

from datetime import datetime, timedelta, timezone

from app.models import Modality, Report, ReportDraft, Study, StudyStatus

_BASE = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)


def _seed() -> dict[str, Study]:
    rows = [
        ("ST-1001", "Somchai P.", Modality.CT, "Chest"),
        ("ST-1002", "Malee K.", Modality.MR, "Brain"),
        ("ST-1003", "Anan T.", Modality.XR, "Chest"),
        ("ST-1004", "Pim S.", Modality.US, "Abdomen"),
        ("ST-1005", "Nattapong R.", Modality.CT, "Abdomen"),
        ("ST-1006", "Wanida L.", Modality.MR, "Spine"),
    ]
    return {
        sid: Study(
            id=sid,
            patient_name=name,
            modality=modality,
            body_part=part,
            status=StudyStatus.PENDING,
            acquired_at=_BASE + timedelta(minutes=17 * i),
        )
        for i, (sid, name, modality, part) in enumerate(rows)
    }


studies: dict[str, Study] = _seed()
reports: dict[str, Report] = {}
drafts: dict[str, ReportDraft] = {}


def reset() -> None:
    """Restore seed state — used by the UI's reset button so the demo is repeatable."""
    global studies, reports, drafts
    studies = _seed()
    reports = {}
    drafts = {}
