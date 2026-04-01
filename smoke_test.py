# -*- coding: utf-8 -*-
"""最小健康檢查：快速驗證專案可載入與核心模組可初始化。"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULES = [
    'config',
    'stock_list',
    'utils',
    'technical_indicators',
    'institutional_tracker',
    'price_volume_alert',
    'support_resistance',
    'history_saver',
    'data_fetcher',
    'app',
    'main',
]


def assert_true(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def smoke_imports() -> None:
    for mod in MODULES:
        importlib.import_module(mod)


def smoke_data_fetcher() -> None:
    from data_fetcher import DataFetcher

    fetcher = DataFetcher()
    assert_true(hasattr(fetcher, '_host_locks_guard'), 'DataFetcher 缺少 _host_locks_guard')
    assert_true(hasattr(fetcher, '_host_min_interval'), 'DataFetcher 缺少 _host_min_interval')
    assert_true(fetcher._safe_int('1,234') == 1234, '_safe_int 轉換異常')
    assert_true(fetcher._safe_float('12.5') == 12.5, '_safe_float 轉換異常')
    assert_true(fetcher._parse_date_to_iso('115/03/04') == '2026-03-04', '日期轉換異常')


def smoke_config_weights() -> None:
    from config import CONFIG

    keys = {'technical', 'institutional', 'price_volume', 'support_resistance'}
    assert_true('weights' in CONFIG, 'CONFIG 缺少 weights')
    assert_true(keys.issubset(CONFIG['weights'].keys()), 'CONFIG 權重鍵不完整')


def main() -> int:
    sys.path.insert(0, str(ROOT))

    smoke_imports()
    smoke_data_fetcher()
    smoke_config_weights()

    print('SMOKE TEST PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
