"""Generate deterministic tabular inputs without repository data files."""

import csv
from io import StringIO

from crossborder_domain import DataDomain


def _csv_bytes(title: str, headers: tuple[str, ...], rows: tuple[tuple[object, ...], ...]) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([title])
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode()


def dataset_csv(domain: DataDomain) -> bytes:
    factories = {
        DataDomain.ORDERS: lambda: _csv_bytes(
            "订单明细 (自动生成测试输入)",
            (
                "订单ID",
                "订单明细ID",
                "商品ID",
                "商家SKU",
                "下单时间",
                "源时区",
                "市场",
                "币种",
                "数量",
                "商品单价",
                "订单金额",
                "折扣",
                "订单状态",
            ),
            (
                (
                    "O-1001",
                    "OI-1001-1",
                    "P-001",
                    "SKU-001",
                    "2026-08-20 09:30:00",
                    "Asia/Shanghai",
                    "US",
                    "USD",
                    2,
                    "29.99",
                    "59.98",
                    "5.00",
                    "paid",
                ),
                (
                    "O-1002",
                    "OI-1002-1",
                    "P-002",
                    "SKU-002",
                    "2026-08-21T10:00:00Z",
                    "UTC",
                    "GB",
                    "GBP",
                    1,
                    "39.00",
                    "39.00",
                    0,
                    "shipped",
                ),
            ),
        ),
        DataDomain.PRODUCTS: lambda: _csv_bytes(
            "商品主数据 (自动生成测试输入)",
            ("商品ID", "商家SKU", "商品标题", "类目", "市场", "币种", "售价", "商品状态"),
            (
                ("P-001", "SKU-001", "便携收纳包", "Home Storage", "US", "USD", "29.99", "active"),
                ("P-002", "SKU-002", "旅行水杯", "Sports", "GB", "GBP", "39.00", "active"),
            ),
        ),
        DataDomain.COSTS: lambda: _csv_bytes(
            "成本档案 (自动生成测试输入)",
            ("商家SKU", "生效日期", "币种", "商品成本", "平台费率", "支付费率", "物流成本", "税率"),
            (
                ("SKU-001", "2026-08-01", "USD", "8.50", "8%", "3%", "4.20", "5%"),
                ("SKU-002", "2026-08-01", "GBP", "12.00", "0.08", "0.03", "5.50", "0.05"),
            ),
        ),
        DataDomain.INVENTORY: lambda: _csv_bytes(
            "库存快照 (自动生成测试输入)",
            ("商家SKU", "快照日期", "仓库编码", "可售库存", "在途库存", "安全库存", "交期天数"),
            (
                ("SKU-001", "2026-08-20", "US-WH-01", 120, 200, 50, 14),
                ("SKU-002", "2026-08-20", "GB-WH-01", 30, 0, 40, 21),
            ),
        ),
        DataDomain.REFUNDS: lambda: _csv_bytes(
            "退款数据 (自动生成测试输入)",
            (
                "退款ID",
                "订单ID",
                "订单明细ID",
                "退款时间",
                "源时区",
                "币种",
                "退款金额",
                "退款原因",
            ),
            (
                (
                    "R-001",
                    "O-1001",
                    "OI-1001-1",
                    "2026-08-25 12:00:00",
                    "Asia/Shanghai",
                    "USD",
                    "29.99",
                    "尺寸不符合预期",
                ),
                (
                    "R-002",
                    "O-1002",
                    "OI-1002-1",
                    "2026-08-26T08:00:00Z",
                    "UTC",
                    "GBP",
                    "39.00",
                    "运输破损",
                ),
            ),
        ),
        DataDomain.REVIEWS: lambda: _csv_bytes(
            "评价数据 (自动生成测试输入)",
            ("评价ID", "商品ID", "评价时间", "源时区", "评分", "评价内容", "市场", "语言"),
            (
                (
                    "RV-001",
                    "P-001",
                    "2026-08-23 10:00:00",
                    "America/Los_Angeles",
                    5,
                    "收纳方便且做工扎实",
                    "US",
                    "zh",
                ),
                (
                    "RV-002",
                    "P-002",
                    "2026-08-24T09:00:00Z",
                    "UTC",
                    2,
                    "杯盖在运输中损坏",
                    "GB",
                    "zh",
                ),
            ),
        ),
        DataDomain.CURRENCY_RATES: lambda: _csv_bytes(
            "汇率数据 (自动生成测试输入)",
            ("汇率日期", "基准币种", "报价币种", "汇率", "汇率来源"),
            (
                ("2026-08-20", "USD", "CNY", "7.1000", "test-factory"),
                ("2026-08-20", "GBP", "CNY", "9.2000", "test-factory"),
            ),
        ),
        DataDomain.CREATIVES: lambda: _csv_bytes(
            "素材元数据 (自动生成测试输入)",
            (
                "素材ID",
                "素材名称",
                "素材类型",
                "商品ID",
                "创建时间",
                "源时区",
                "语言",
                "市场",
                "素材地址",
            ),
            (
                (
                    "CR-001",
                    "收纳前后对比",
                    "video",
                    "P-001",
                    "2026-08-10 09:00:00",
                    "Asia/Shanghai",
                    "en",
                    "US",
                    "memory://creative-001.mp4",
                ),
                (
                    "CR-002",
                    "水杯场景图",
                    "image",
                    "P-002",
                    "2026-08-11T09:00:00Z",
                    "UTC",
                    "en",
                    "GB",
                    "memory://creative-002.png",
                ),
            ),
        ),
    }
    try:
        return factories[domain]()
    except KeyError as exc:
        raise ValueError(f"没有为 {domain.value} 定义测试输入工厂") from exc
