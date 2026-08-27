"""TikTok Ads connector configuration boundary.

Network synchronization is intentionally added only after credentials, retry,
pagination, and fixture-based contract tests are available.
"""

from pydantic import Field, SecretStr

from crossborder_domain.common import StrictDomainModel

TIKTOK_BUSINESS_API_BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
INTEGRATED_REPORT_PATH = "/report/integrated/get/"


class TikTokAdsConfig(StrictDomainModel):
    access_token: SecretStr
    advertiser_id: str = Field(min_length=1, max_length=128)
    base_url: str = TIKTOK_BUSINESS_API_BASE_URL


def build_report_url(config: TikTokAdsConfig) -> str:
    return f"{config.base_url.rstrip('/')}{INTEGRATED_REPORT_PATH}"
