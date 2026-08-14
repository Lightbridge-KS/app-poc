"""The single source of truth.

Every TypeScript type in the frontend is derived from this file. Nothing here is
written twice on the other side of the wire — if it changes, the frontend stops
compiling.

Several choices below exist to demonstrate the gotchas from
``docs/design/openapi-spec-from-pydantic.md``; they are marked GOTCHA.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class Modality(str, Enum):
    """GOTCHA #4 — inheriting ``str`` makes this a string literal union in TS.

    Without the ``str`` base these land as opaque integers and the frontend
    ``<select>`` loses all meaning.
    """

    CT = "CT"
    MR = "MR"
    XR = "XR"
    US = "US"


class StudyStatus(str, Enum):
    PENDING = "pending"
    REPORTED = "reported"


class Study(BaseModel):
    id: str
    patient_name: str
    modality: Modality
    body_part: str
    status: StudyStatus
    # GOTCHA #3 — a datetime crosses the wire as an ISO string and arrives in TS
    # as `string`, not `Date`. The frontend parses it once, at the boundary.
    acquired_at: datetime


class ReportIn(BaseModel):
    """The request body. Type-checked against the TS call site."""

    findings: str = Field(min_length=1, description="What was seen.")
    impression: str = Field(min_length=1, description="What it means.")
    critical: bool = False


class ReportDraft(BaseModel):
    """An autosaved, partially-filled report — sent in, echoed back.

    GOTCHA #1 — and the PoC's one correction to the source doc.

    The doc says a model with defaults splits into `FooInput`/`FooOutput`, and
    that `separate_input_output_schemas=False` collapses it. On FastAPI 0.141 +
    Pydantic 2.13, **neither half of that is still true**:

    * A plain default no longer splits anything. Pydantic 2.13 emits identical
      validation and serialization schemas for `ReportIn` above, so there is
      only ever one `ReportIn`.
    * What splits a model now is a genuine divergence between those two
      schemas — here the `is_complete` computed field, which the server derives
      and the client must never send.
    * And that split **ignores the flag**. See `fastapi/_compat/v2.py`:
      `separate_input_output_schemas or _has_computed_fields(field)` — a
      computed field forces separation either way. `just gotchas` proves it by
      flipping the flag and showing the spec does not change.

    The fix is therefore not a flag but a modelling decision: let the split
    stand and treat `-Input`/`-Output` as the two genuinely different shapes
    they are, or drop the computed field and derive it client-side. This PoC
    lets it stand — see `docs/GOTCHAS.md`.
    """

    findings: str = ""
    impression: str = ""
    critical: bool = False

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Server-derived: output-only, never part of the request."""
        return bool(self.findings.strip() and self.impression.strip())


class Report(BaseModel):
    study_id: str
    findings: str
    impression: str
    critical: bool = False
    created_at: datetime


class ErrorOut(BaseModel):
    """GOTCHA #5 — declared per-route in ``responses=`` so the TS error branch
    is narrowed instead of falling back to an untyped blob."""

    code: str
    message: str
