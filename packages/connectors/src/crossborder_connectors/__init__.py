"""External data connector contracts and tabular ingestion helpers."""

from crossborder_connectors.advertising import preview_advertising_file
from crossborder_connectors.base import (
    Connector,
    ConnectorBatch,
    ConnectorError,
    ConnectorErrorCode,
    SyncRequest,
)
from crossborder_connectors.mapping import ADVERTISING_FIELD_ALIASES, map_advertising_headers
from crossborder_connectors.synthetic import SyntheticAdvertisingConnector

__all__ = [
    "ADVERTISING_FIELD_ALIASES",
    "Connector",
    "ConnectorBatch",
    "ConnectorError",
    "ConnectorErrorCode",
    "SyncRequest",
    "SyntheticAdvertisingConnector",
    "map_advertising_headers",
    "preview_advertising_file",
]
