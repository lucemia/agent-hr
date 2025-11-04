"""Pytest configuration and fixtures."""

from io import StringIO

import pandas as pd
import pytest


@pytest.fixture
def sample_lrs_csv_data():
    """Sample LRS CSV data for testing."""
    return """編號,名字,作答email,履歷,補充說明By LRS,測驗結果,筆試分數,是否約面,補充說明 By集雅
1,張三,zhang.san@example.com,zhang_san_resume.pdf,,https://example.com/test1,85,是,
2,李四,li.si@example.com,li_si_resume.pdf,優秀候選人,https://example.com/test2,92,約面,技術能力強
3,王五,wang.wu@example.com,wang_wu_resume.pdf,,https://example.com/test3,78,否,"""


@pytest.fixture
def sample_cake_csv_data():
    """Sample Cake CSV data for testing."""
    return """名字,email,分數,測驗結果,履歷,是否約面,是否約面.1,職缺,補充說明,Comment,FROM
Sidney Lu,sidney@example.com,69%,https://example.com/test1,,False,,,,
Vanna Chen,vanna@example.com,67%,https://example.com/test2,resume.pdf,False,,後端工程師,年薪約130萬,,
Tony Xiao,tony@example.com,87%,https://example.com/test3,tony_resume.pdf,True,,後端工程師,管理經驗豐富,優秀候選人,cake"""


@pytest.fixture
def sample_lrs_dataframe(sample_lrs_csv_data):
    """Sample LRS DataFrame for testing."""
    return pd.read_csv(StringIO(sample_lrs_csv_data))


@pytest.fixture
def sample_cake_dataframe(sample_cake_csv_data):
    """Sample Cake DataFrame for testing."""
    return pd.read_csv(StringIO(sample_cake_csv_data))


@pytest.fixture
def mock_requests_response():
    """Mock requests response for testing."""

    class MockResponse:
        def __init__(self, text, status_code=200):
            self.text = text
            self.status_code = status_code
            self.encoding = "utf-8"

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    return MockResponse
