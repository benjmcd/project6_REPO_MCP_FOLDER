from __future__ import annotations

from app.services.layer3_pass_entry import Layer3PassEntryError
from app.services.layer3_qual_aps_execution import Layer3QualApsExecutionError
from app.services.layer3_workbench_error import Layer3WorkbenchError


def analysis_execution_start_workbench_error(
    exc: Layer3PassEntryError | Layer3QualApsExecutionError,
) -> Layer3WorkbenchError:
    return Layer3WorkbenchError(
        "analysis_execution_start_not_admitted",
        str(exc),
        status="conflict",
        http_status=409,
    )
