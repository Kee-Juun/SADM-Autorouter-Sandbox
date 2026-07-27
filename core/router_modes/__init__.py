"""Router-mode identity, presentation metadata, and legacy compatibility.

The registry remains data-only. The compatibility wrapper lazy-loads the unchanged
workflow only when called. Non-browser orchestration policy lives in the sibling
``orchestration`` module. Specialized delegating wrappers live in ``handlers``;
Selenium behavior remains in the existing router methods.
"""

from .registry import (
    MODE_REGISTRY,
    MODE_SPECS,
    ModeSpec,
    get_mode_spec,
    iter_mode_specs,
)
from .compatibility import (
    LEGACY_MODE_PRECEDENCE,
    LegacyModeFlags,
    flags_for_mode,
    mode_from_flags,
    normalize_mode,
    run_automation_for_mode,
)

__all__ = [
    "LEGACY_MODE_PRECEDENCE",
    "MODE_REGISTRY",
    "MODE_SPECS",
    "LegacyModeFlags",
    "ModeSpec",
    "flags_for_mode",
    "get_mode_spec",
    "iter_mode_specs",
    "mode_from_flags",
    "normalize_mode",
    "run_automation_for_mode",
]
