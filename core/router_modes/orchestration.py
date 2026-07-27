"""Non-browser orchestration policy for router modes.

This module describes run identity, batch labels, and row-scope selection. It does
not import pandas, extractors, workflow code, router code, or Selenium. Callers supply
the existing row predicates so their behavior remains authoritative.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from .compatibility import LegacyModeFlags, mode_from_flags, normalize_mode
from .registry import get_mode_spec


SCOPE_FLAG_PRECEDENCE = (
    ("itc_mode", "itc"),
    ("irsplr_mode", "irsplr"),
    ("ohtax0_mode", "ohtax0"),
    ("mnsutb_mode", "mnsutb"),
)

EMPTY_SCOPE_MESSAGES = {
    "itc": "ITC Autorouter mode found no FDITC000/FDITCALJ rows to process.",
    "irsplr": (
        "IRSPLR Autorouter mode found no "
        "FDIRSPLR/FDPLR000/FDCCA001 rows to process."
    ),
    "ohtax0": "OHTAX0 Autorouter mode found no STOHTAX0 rows to process.",
    "mnsutb": "MNSUTB Autorouter mode found no STMNSUTB rows to process.",
}

BATCH_TYPES = {
    "smd": ("counsel", "main"),
    "dar": ("counsel", "main"),
    "mspb": ("mspb",),
    "itc": ("itc",),
    "irsplr": ("irsplr",),
    "ohtax0": ("ohtax0",),
    "mnsutb": ("mnsutb",),
}

INITIAL_STATUS = {
    "smd": "Counsel Batch Started",
    "dar": "Counsel Batch Started",
    "mspb": "MSPB Batch Started",
    "itc": "ITC Batch Started",
    "irsplr": "IRSPLR Batch Started",
    "ohtax0": "OHTAX0 Batch Started",
    "mnsutb": "MNSUTB Batch Started",
}


@dataclass(frozen=True)
class ModeRunPlan:
    """Stable non-browser orchestration metadata for one run mode."""

    mode_key: str
    router_label: str
    document_only: bool
    batch_types: Tuple[str, ...]
    initial_status: str

    @property
    def primary_batch(self) -> str:
        """Return the mode-specific batch or the first legacy batch."""

        return self.batch_types[0]


@dataclass(frozen=True)
class RunScopeSelection:
    """Selected rows plus the legacy empty-scope message, when applicable."""

    rows: Any
    scope_key: Optional[str]
    empty_scope_message: Optional[str]


def get_mode_run_plan(mode: Any) -> ModeRunPlan:
    """Build the run plan for a canonical key, falling back to SMD."""

    mode_key = normalize_mode(mode)
    spec = get_mode_spec(mode_key)
    return ModeRunPlan(
        mode_key=mode_key,
        router_label=spec.router_label,
        document_only=spec.document_only,
        batch_types=BATCH_TYPES[mode_key],
        initial_status=INITIAL_STATUS[mode_key],
    )


def run_plan_from_flags(flags: LegacyModeFlags) -> ModeRunPlan:
    """Build a run plan using the legacy mode-identity precedence."""

    return get_mode_run_plan(mode_from_flags(flags))


def scope_key_from_flags(flags: LegacyModeFlags) -> Optional[str]:
    """Return the legacy court-specific scope key.

    Scope precedence intentionally differs from mode identity precedence: MSPB and
    DAR do not restrict the input rows, while ITC and the later court modes do.
    """

    for flag_name, scope_key in SCOPE_FLAG_PRECEDENCE:
        if getattr(flags, flag_name):
            return scope_key
    return None


def select_run_scope(
    dataframe: Any,
    flags: LegacyModeFlags,
    row_predicates: Mapping[str, Any],
) -> RunScopeSelection:
    """Apply the existing court-row predicate selected by legacy scope precedence."""

    scope_key = scope_key_from_flags(flags)
    if scope_key is None:
        return RunScopeSelection(
            rows=dataframe,
            scope_key=None,
            empty_scope_message=None,
        )

    predicate = row_predicates[scope_key]
    selected_rows = dataframe[dataframe.apply(predicate, axis=1)].copy()
    return RunScopeSelection(
        rows=selected_rows,
        scope_key=scope_key,
        empty_scope_message=(
            EMPTY_SCOPE_MESSAGES[scope_key] if selected_rows.empty else None
        ),
    )
