"""Deterministic connector used for demos and contract tests only."""

from datetime import timedelta
from decimal import Decimal

from crossborder_connectors.base import ConnectorBatch, SyncRequest
from crossborder_domain import AdvertisingRecord


class SyntheticAdvertisingConnector:
    name = "synthetic_advertising"

    async def fetch(self, request: SyncRequest) -> ConnectorBatch[AdvertisingRecord]:
        records: list[AdvertisingRecord] = []
        current = request.start_date
        sequence = 1
        while current <= request.end_date:
            records.append(
                AdvertisingRecord(
                    report_date=current,
                    campaign_id="demo-campaign-001",
                    campaign_name="合成演示广告系列",
                    currency="USD",
                    impressions=1000 * sequence,
                    clicks=50 * sequence,
                    spend=Decimal("100.00") * sequence,
                    orders=5 * sequence,
                    revenue=Decimal("300.00") * sequence,
                    source_row_number=sequence + 1,
                    idempotency_key=f"{sequence:064x}",
                )
            )
            current += timedelta(days=1)
            sequence += 1
        return ConnectorBatch(records=records)
