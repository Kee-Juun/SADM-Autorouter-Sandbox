"""Compatibility helpers between canonical mode keys and legacy mode flags.

The existing workflow remains the routing implementation. These helpers centralize
flag conversion while preserving its historical precedence and fallback behavior.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict

from .registry import MODE_REGISTRY


LEGACY_MODE_PRECEDENCE = (
    ("mspb_mode", "mspb"),
    ("itc_mode", "itc"),
    ("irsplr_mode", "irsplr"),
    ("ohtax0_mode", "ohtax0"),
    ("mnsutb_mode", "mnsutb"),
    ("mework_mode", "mework"),
    ("mosu00_mode", "mosu00"),
    ("dar_mode", "dar"),
)


@dataclass(frozen=True)
class LegacyModeFlags:
    """Boolean mode arguments accepted by the existing workflow."""

    dar_mode: bool = False
    wc_mode: bool = False
    mspb_mode: bool = False
    itc_mode: bool = False
    irsplr_mode: bool = False
    ohtax0_mode: bool = False
    mnsutb_mode: bool = False
    mework_mode: bool = False
    mosu00_mode: bool = False

    def as_workflow_kwargs(self) -> Dict[str, bool]:
        """Return a fresh keyword-argument mapping for the legacy workflow."""

        kwargs = asdict(self)
        if not self.mework_mode:
            kwargs.pop("mework_mode")
        if not self.mosu00_mode:
            kwargs.pop("mosu00_mode")
        return kwargs


def normalize_mode(mode: Any = None, *, dar_mode: bool = False) -> str:
    """Return a supported key using the current SMD/DAR fallback behavior."""

    if mode is None:
        return "dar" if dar_mode else "smd"

    normalized = str(mode).strip().lower()
    return normalized if normalized in MODE_REGISTRY else "smd"


def flags_for_mode(mode: Any = None, *, dar_mode: bool = False) -> LegacyModeFlags:
    """Expand one canonical mode into the workflow's legacy boolean arguments."""

    normalized = normalize_mode(mode, dar_mode=dar_mode)
    return LegacyModeFlags(
        dar_mode=normalized == "dar",
        mspb_mode=normalized == "mspb",
        itc_mode=normalized == "itc",
        irsplr_mode=normalized == "irsplr",
        ohtax0_mode=normalized == "ohtax0",
        mnsutb_mode=normalized == "mnsutb",
        mework_mode=normalized == "mework",
        mosu00_mode=normalized == "mosu00",
    )


def mode_from_flags(flags: LegacyModeFlags) -> str:
    """Collapse legacy flags using the workflow's existing precedence."""

    for flag_name, mode_key in LEGACY_MODE_PRECEDENCE:
        if getattr(flags, flag_name):
            return mode_key
    return "smd"


def run_automation_for_mode(mode: Any, **workflow_kwargs):
    """Delegate to the unchanged workflow using flags derived from ``mode``."""

    from ..smducar_workflow import run_automation_workflow

    delegated_kwargs = dict(workflow_kwargs)
    delegated_kwargs.update(flags_for_mode(mode).as_workflow_kwargs())
    return run_automation_workflow(**delegated_kwargs)
