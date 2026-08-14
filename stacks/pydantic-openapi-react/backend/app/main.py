"""App factory — and the one place the OpenAPI *shape* is tuned.

Two environment toggles exist purely so `just gotchas` can export a second spec
with the settings flipped and diff the two. Normal runs never set them.
"""

import os
import re

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.routing import generate_unique_id as fastapi_default_unique_id

from app.errors import ApiError, api_error_handler
from app.routes import router


def camel_operation_id(route: APIRoute) -> str:
    """GOTCHA #2 — turn `create_report` into `createReport`.

    FastAPI's default id is built from path + method, producing
    `create_report_studies__study_id__report_post`. That name is what SDK
    generators use for their function and hook names, so it is worth overriding
    once here rather than living with it in every call site.
    """
    head, *tail = re.split(r"_+", route.name)
    return head + "".join(word.capitalize() for word in tail)


def _flag(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes"}


def create_app() -> FastAPI:
    # GOTCHA #1 — kept at False to document intent, but on FastAPI 0.141 +
    # Pydantic 2.13 this flag no longer changes the emitted spec at all.
    # `just gotchas` flips it and shows the diff is empty. See ReportDraft in
    # models.py for why, and what to do instead.
    separate_io = _flag("POC_SEPARATE_IO")
    ugly_ids = _flag("POC_UGLY_IDS")

    app = FastAPI(
        title="Radiology Studies PoC",
        version="0.1.0",
        summary="Pydantic models are the contract; TypeScript is generated downstream.",
        separate_input_output_schemas=separate_io,
        generate_unique_id_function=(
            fastapi_default_unique_id if ugly_ids else camel_operation_id
        ),
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router)
    return app


app = create_app()
