from io import BytesIO

from openpyxl import Workbook

from crossborder_connectors import map_advertising_headers, preview_advertising_file
from crossborder_domain import MappingStatus


def _advertising_csv() -> bytes:
    return """TikTok Ads 广告数据日报
日期,广告系列ID,广告系列名称,币种,展示次数,点击次数,消耗,订单数,成交金额,备注
2026-08-20,C-001,新品冷启动,USD,"10,000",500,250,25,1000,合成数据
2026-08-20,C-001,新品冷启动,USD,"10,000",500,250,25,1000,重复数据
2026-08-21,C-002,异常样例,USD,100,150,20,1,30,点击大于展示
2026-08-21,C-003,利润款测试,USD,5000,200,50,10,200,合成数据
""".encode()


def test_header_mapping_supports_chinese_aliases_and_unknown_columns() -> None:
    mappings = map_advertising_headers(["报告日期", "广告计划ID", "GMV", "自定义标签"])

    assert [mapping.canonical_field for mapping in mappings] == [
        "report_date",
        "campaign_id",
        "revenue",
        None,
    ]
    assert mappings[-1].status is MappingStatus.UNMAPPED


def test_preview_detects_title_row_bad_rows_duplicates_and_metrics() -> None:
    preview = preview_advertising_file(_advertising_csv(), "tiktok.csv")

    assert preview.header_row_number == 2
    assert preview.source_row_count == 4
    assert preview.accepted_row_count == 2
    assert preview.rejected_row_count == 2
    assert preview.unknown_columns == ["备注"]
    assert {issue.code for issue in preview.issues} == {"duplicate_row", "invalid_row"}
    assert preview.aggregate_metrics["spend"] == 300
    assert preview.aggregate_metrics["revenue"] == 1200
    assert preview.aggregate_metrics["roas"] == 4


def test_xlsx_reader_uses_the_same_governance_pipeline() -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["日期", "广告系列ID", "币种", "展示次数", "点击次数", "消耗", "订单数", "GMV"])
    sheet.append(["2026-08-20", "C-001", "USD", 1000, 50, 100, 5, 300])
    content = BytesIO()
    workbook.save(content)

    preview = preview_advertising_file(content.getvalue(), "tiktok.xlsx")

    assert preview.accepted_row_count == 1
    assert preview.records[0].campaign_id == "C-001"


def test_missing_required_columns_rejects_data_before_import() -> None:
    content = "日期,广告系列ID,GMV\n2026-08-20,C-001,300\n".encode()

    preview = preview_advertising_file(content, "missing.csv")

    assert preview.accepted_row_count == 0
    assert preview.rejected_row_count == 1
    assert any(issue.code == "missing_required_field" for issue in preview.issues)
