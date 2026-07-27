"""Immutable registry of supported router-mode metadata.

Keep this module free of GUI, workflow, parsing, and Selenium dependencies. It is a
single source of truth for stable mode identity and low-risk presentation metadata;
it does not select rows or perform routing.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple


@dataclass(frozen=True)
class ModeSpec:
    """Stable identity and presentation metadata for one selectable router mode."""

    key: str
    display_name: str
    router_label: str
    progress_batch: str
    result_label: str
    document_only: bool


MODE_SPECS: Tuple[ModeSpec, ...] = (
    ModeSpec(
        key="smd",
        display_name="SMD Autorouter",
        router_label="SADM",
        progress_batch="main",
        result_label="SMD USAP",
        document_only=False,
    ),
    ModeSpec(
        key="dar",
        display_name="DAR Autoruter",
        router_label="DAR",
        progress_batch="main",
        result_label="DAR",
        document_only=False,
    ),
    ModeSpec(
        key="mspb",
        display_name="MSPB Autorouter",
        router_label="MSPB",
        progress_batch="mspb",
        result_label="MSPB",
        document_only=True,
    ),
    ModeSpec(
        key="itc",
        display_name="ITC Autorouter",
        router_label="ITC",
        progress_batch="itc",
        result_label="ITC",
        document_only=True,
    ),
    ModeSpec(
        key="irsplr",
        display_name="IRSPLR Autorouter",
        router_label="IRSPLR",
        progress_batch="irsplr",
        result_label="IRSPLR",
        document_only=True,
    ),
    ModeSpec(
        key="ohtax0",
        display_name="OHTAX0 Autorouter",
        router_label="OHTAX0",
        progress_batch="ohtax0",
        result_label="OHTAX0",
        document_only=True,
    ),
    ModeSpec(
        key="mnsutb",
        display_name="MNSUTB Autorouter",
        router_label="MNSUTB",
        progress_batch="mnsutb",
        result_label="MNSUTB",
        document_only=True,
    ),
)

MODE_REGISTRY: Mapping[str, ModeSpec] = MappingProxyType(
    {mode.key: mode for mode in MODE_SPECS}
)


def iter_mode_specs() -> Tuple[ModeSpec, ...]:
    """Return selectable modes in their stable GUI order."""

    return MODE_SPECS


def get_mode_spec(mode_key: str) -> ModeSpec:
    """Return the registered mode or raise ``KeyError`` for an unknown key."""

    return MODE_REGISTRY[mode_key]
