from datetime import date

from crossborder_connectors import SyncRequest, SyntheticAdvertisingConnector


async def test_synthetic_connector_is_deterministic_and_explicitly_named() -> None:
    connector = SyntheticAdvertisingConnector()
    batch = await connector.fetch(
        SyncRequest(
            organization_id="demo-company",
            start_date=date(2026, 8, 20),
            end_date=date(2026, 8, 21),
        )
    )

    assert connector.name == "synthetic_advertising"
    assert len(batch.records) == 2
    assert batch.records[0].campaign_name == "合成演示广告系列"
    assert batch.records[1].revenue > batch.records[0].revenue
