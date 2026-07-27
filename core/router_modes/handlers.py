"""Delegating wrappers for specialized document-mode router methods.

Handlers in this module contain no Selenium logic. They name existing CaseLawRouter
methods and forward calls without changing arguments, ordering, or return values.
SMD and DAR intentionally remain on the router's shared legacy path.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Optional


_UNSET = object()


@dataclass(frozen=True)
class DocumentModeHandler:
    """Method-name adapter for one specialized document mode."""

    key: str
    metadata_keyword: str
    record_method_name: str
    extract_method_name: str
    fill_method_name: str
    postprocess_method_name: Optional[str] = None

    def record_metadata(
        self,
        router: Any,
        row_index: Any,
        row: Any,
        lni: Any,
        *,
        metadata: Any = _UNSET,
        metadata_status: str = "Attempted",
    ) -> Any:
        """Delegate metadata recording to the existing router method."""

        method = getattr(router, self.record_method_name)
        kwargs = {"metadata_status": metadata_status}
        if metadata is not _UNSET:
            kwargs["metadata"] = metadata
        return method(row_index, row, lni, **kwargs)

    def extract_metadata(self, router: Any, row: Any, row_index: Any) -> Any:
        """Delegate metadata extraction to the existing router method."""

        return getattr(router, self.extract_method_name)(row, row_index)

    def postprocess_metadata(
        self,
        router: Any,
        row_index: Any,
        row: Any,
        lni: Any,
        metadata: Any,
    ) -> Any:
        """Delegate optional mode-specific postprocessing, otherwise pass through."""

        if not self.postprocess_method_name:
            return metadata
        return getattr(router, self.postprocess_method_name)(
            row_index,
            row,
            lni,
            metadata,
        )

    def fill_form(
        self,
        router: Any,
        row: Any,
        row_index: Any,
        metadata: Any,
    ) -> Any:
        """Delegate form filling to the existing specialized router method."""

        return getattr(router, self.fill_method_name)(row, row_index, metadata)


DOCUMENT_MODE_HANDLERS: Mapping[str, DocumentModeHandler] = MappingProxyType(
    {
        "mspb": DocumentModeHandler(
            key="mspb",
            metadata_keyword="mspb_metadata",
            record_method_name="record_mspb_metadata",
            extract_method_name="extract_mspb_metadata_from_search_result",
            fill_method_name="fill_mspb_irt_form",
        ),
        "itc": DocumentModeHandler(
            key="itc",
            metadata_keyword="itc_metadata",
            record_method_name="record_itc_metadata",
            extract_method_name="extract_itc_metadata_from_search_result",
            fill_method_name="fill_itc_irt_form",
            postprocess_method_name="mark_itc_duplicate_status",
        ),
        "irsplr": DocumentModeHandler(
            key="irsplr",
            metadata_keyword="irsplr_metadata",
            record_method_name="record_irsplr_metadata",
            extract_method_name="extract_irsplr_metadata_from_search_result",
            fill_method_name="fill_irsplr_irt_form",
        ),
        "ohtax0": DocumentModeHandler(
            key="ohtax0",
            metadata_keyword="ohtax0_metadata",
            record_method_name="record_ohtax0_metadata",
            extract_method_name="extract_ohtax0_metadata_from_search_result",
            fill_method_name="fill_ohtax0_irt_form",
        ),
        "mnsutb": DocumentModeHandler(
            key="mnsutb",
            metadata_keyword="mnsutb_metadata",
            record_method_name="record_mnsutb_metadata",
            extract_method_name="extract_mnsutb_metadata_from_search_result",
            fill_method_name="fill_mnsutb_irt_form",
        ),
    }
)


def get_document_mode_handler(mode_key: str) -> DocumentModeHandler:
    """Return the specialized handler registered for ``mode_key``."""

    return DOCUMENT_MODE_HANDLERS[mode_key]


def select_row_mode_handler(
    *,
    mspb_mode: bool = False,
    row_is_itc: bool = False,
    irsplr_mode: bool = False,
    row_is_irsplr: bool = False,
    ohtax0_mode: bool = False,
    row_is_ohtax0: bool = False,
    mnsutb_mode: bool = False,
    row_is_mnsutb: bool = False,
) -> Optional[DocumentModeHandler]:
    """Select a row handler using the exact existing process-batch precedence."""

    if mspb_mode:
        return DOCUMENT_MODE_HANDLERS["mspb"]
    if row_is_itc:
        return DOCUMENT_MODE_HANDLERS["itc"]
    if irsplr_mode or row_is_irsplr:
        return DOCUMENT_MODE_HANDLERS["irsplr"]
    if ohtax0_mode or row_is_ohtax0:
        return DOCUMENT_MODE_HANDLERS["ohtax0"]
    if mnsutb_mode or row_is_mnsutb:
        return DOCUMENT_MODE_HANDLERS["mnsutb"]
    return None


def select_form_mode_handler(
    *,
    mspb_mode: bool = False,
    metadata_by_mode: Mapping[str, Any],
) -> Optional[DocumentModeHandler]:
    """Select a form handler using the exact existing fill-form precedence."""

    if mspb_mode:
        return DOCUMENT_MODE_HANDLERS["mspb"]
    for mode_key in ("itc", "irsplr", "ohtax0", "mnsutb"):
        if metadata_by_mode.get(mode_key):
            return DOCUMENT_MODE_HANDLERS[mode_key]
    return None
