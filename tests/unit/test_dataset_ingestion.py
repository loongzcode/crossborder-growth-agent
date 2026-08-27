from pathlib import Path

import pytest

from crossborder_connectors import preview_dataset_file
from crossborder_domain import CostRecord, DataDomain, OrderRecord

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("domain", "filename"),
    [
        (DataDomain.ORDERS, "orders_sample.csv"),
        (DataDomain.PRODUCTS, "products_sample.csv"),
        (DataDomain.COSTS, "costs_sample.csv"),
        (DataDomain.INVENTORY, "inventory_sample.csv"),
        (DataDomain.REFUNDS, "refunds_sample.csv"),
        (DataDomain.REVIEWS, "reviews_sample.csv"),
        (DataDomain.CURRENCY_RATES, "currency_rates_sample.csv"),
        (DataDomain.CREATIVES, "creatives_sample.csv"),
    ],
)
def test_all_standard_dataset_samples_pass_the_same_quality_gate(
    domain: DataDomain, filename: str
) -> None:
    content = (ROOT / "data" / "samples" / filename).read_bytes()

    preview = preview_dataset_file(content, filename, domain)

    assert preview.domain is domain
    assert preview.header_row_number == 2
    assert preview.accepted_row_count == 2
    assert preview.rejected_row_count == 0
    assert preview.file_checksum_sha256
    assert preview.schema_version == "2026.08.1"


def test_order_datetime_is_interpreted_with_explicit_source_timezone() -> None:
    content = (ROOT / "data" / "samples" / "orders_sample.csv").read_bytes()

    preview = preview_dataset_file(content, "orders.csv", DataDomain.ORDERS)

    first = preview.records[0]
    assert isinstance(first, OrderRecord)
    assert first.ordered_at.tzinfo is not None
    assert first.source_timezone == "Asia/Shanghai"


def test_percentage_and_decimal_cost_rates_normalize_to_same_scale() -> None:
    content = (ROOT / "data" / "samples" / "costs_sample.csv").read_bytes()

    preview = preview_dataset_file(content, "costs.csv", DataDomain.COSTS)

    first, second = preview.records
    assert isinstance(first, CostRecord)
    assert isinstance(second, CostRecord)
    assert first.platform_fee_rate == second.platform_fee_rate
    assert first.tax_rate == second.tax_rate


def test_invalid_review_rating_is_rejected_without_losing_valid_rows() -> None:
    content = (
        "评价ID,商品ID,评价时间,源时区,评分,评价内容,市场,语言\n"
        "RV-1,P-1,2026-08-20 10:00:00,UTC,5,正常评价,US,zh\n"
        "RV-2,P-1,2026-08-20 11:00:00,UTC,6,异常评分,US,zh\n"
    ).encode()

    preview = preview_dataset_file(content, "reviews.csv", DataDomain.REVIEWS)

    assert preview.accepted_row_count == 1
    assert preview.rejected_row_count == 1
    assert preview.issues[0].code == "invalid_row"


def test_missing_timezone_column_stops_datetime_dataset_before_import() -> None:
    content = (
        "订单ID,订单明细ID,商品ID,商家SKU,下单时间,市场,币种,数量,商品单价,订单金额,订单状态\n"
        "O-1,OI-1,P-1,SKU-1,2026-08-20 10:00:00,US,USD,1,10,10,paid\n"
    ).encode()

    preview = preview_dataset_file(content, "orders.csv", DataDomain.ORDERS)

    assert preview.accepted_row_count == 0
    assert any(issue.column == "source_timezone" for issue in preview.issues)


def test_duplicate_business_grain_with_different_values_is_rejected() -> None:
    content = (
        "商家SKU,快照日期,仓库编码,可售库存,在途库存,安全库存,交期天数\n"
        "SKU-1,2026-08-20,WH-1,100,20,30,14\n"
        "SKU-1,2026-08-20,WH-1,90,20,30,14\n"
    ).encode()

    preview = preview_dataset_file(content, "inventory.csv", DataDomain.INVENTORY)

    assert preview.accepted_row_count == 1
    assert preview.rejected_row_count == 1
    assert preview.issues[0].code == "duplicate_business_key"
