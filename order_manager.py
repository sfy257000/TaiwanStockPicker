# -*- coding: utf-8 -*-
"""
訂單管理器
維護本地訂單狀態，提供高層次下單介面
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sinopac_api import SinoPacTrader, SinoPacAPIError, get_trader


class OrderManager:
    """
    訂單管理器
    包裝 SinoPacTrader，提供更易用的下單介面
    """

    def __init__(self, trader: Optional[SinoPacTrader] = None):
        self.trader = trader or get_trader()

    def buy(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        name: str = '',
        current_price: float = 0,
    ) -> dict:
        """
        買進股票

        Args:
            code: 股票代碼
            quantity: 股數（需為1000倍數）
            price: 限價（0=市價）
            name: 股票名稱
            current_price: 走勢價格（模擬成交用）

        Returns:
            委託結果
        """
        order_type = 'limit' if price > 0 else 'market'
        return self.trader.place_order(
            code=code,
            quantity=quantity,
            action='buy',
            order_type=order_type,
            price=price,
            name=name,
            current_price=current_price,
        )

    def sell(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        name: str = '',
        current_price: float = 0,
    ) -> dict:
        """
        賣出股票

        Args:
            code: 股票代碼
            quantity: 股數（需為1000倍數）
            price: 限價（0=市價）
            name: 股票名稱
            current_price: 走勢價格（模擬成交用）

        Returns:
            委託結果
        """
        order_type = 'limit' if price > 0 else 'market'
        return self.trader.place_order(
            code=code,
            quantity=quantity,
            action='sell',
            order_type=order_type,
            price=price,
            name=name,
            current_price=current_price,
        )

    def cancel(self, order_id: str) -> dict:
        """取消委託"""
        return self.trader.cancel_order(order_id)

    def modify(self, order_id: str, new_price: float = None, new_quantity: int = None) -> dict:
        """修改委託"""
        return self.trader.modify_order(order_id, new_price, new_quantity)

    def get_balance(self) -> dict:
        """取得帳戶餘額"""
        return self.trader.get_balance()

    def get_positions(self) -> list[dict]:
        """取得持有部位"""
        return self.trader.get_positions()

    def get_position(self, code: str) -> dict | None:
        """取得特定股票部位"""
        positions = self.trader.get_positions()
        for pos in positions:
            if pos.get('code') == code:
                return pos
        return None

    def get_orders(self, date: str = None) -> list[dict]:
        """取得委託記錄"""
        return self.trader.get_orders(date)

    def get_pending_orders(self) -> list[dict]:
        """取得待成交委託"""
        all_orders = self.trader.get_orders()
        return [o for o in all_orders if o.get('status') == 'pending']

    def get_filled_orders(self, date: str = None) -> list[dict]:
        """取得已成交委託"""
        all_orders = self.trader.get_orders(date)
        return [o for o in all_orders if o.get('status') == 'filled']

    def get_day_summary(self, date: str = None) -> dict:
        """取得當日交易摘要"""
        date = date or datetime.now().strftime('%Y-%m-%d')
        filled = self.get_filled_orders(date)

        buy_value = sum(
            o.get('filled_quantity', 0) * o.get('avg_fill_price', 0)
            for o in filled if o.get('action') == 'buy'
        )
        sell_value = sum(
            o.get('filled_quantity', 0) * o.get('avg_fill_price', 0)
            for o in filled if o.get('action') == 'sell'
        )
        commission = sum(o.get('commission', 0) for o in filled)
        tax = sum(o.get('tax', 0) for o in filled)

        return {
            'date': date,
            'filled_count': len(filled),
            'buy_count': len([o for o in filled if o.get('action') == 'buy']),
            'sell_count': len([o for o in filled if o.get('action') == 'sell']),
            'pending_count': len(self.get_pending_orders()),
            'buy_value': buy_value,
            'sell_value': sell_value,
            'commission': commission,
            'tax': tax,
        }

    def calculate_position_pnl(self, code: str, current_price: float) -> dict:
        """計算部位損益"""
        pos = self.get_position(code)
        if not pos or pos.get('quantity', 0) <= 0:
            return {'code': code, 'has_position': False}

        quantity = pos['quantity']
        avg_cost = pos['avg_cost']
        market_value = current_price * quantity
        cost = avg_cost * quantity
        pnl = market_value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0

        return {
            'code': code,
            'has_position': True,
            'quantity': quantity,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'market_value': market_value,
            'cost': cost,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
        }

    def reset_account(self) -> dict:
        """重置帳戶（僅模擬模式）"""
        return self.trader.reset_account()

    def export_day_trades(self, date: str = None) -> list[dict]:
        """匯出當日交易"""
        date = date or datetime.now().strftime('%Y-%m-%d')
        filled = self.get_filled_orders(date)

        return [
            {
                '時間': o.get('filled_at', ''),
                '股票代碼': o.get('code', ''),
                '股票名稱': o.get('name', ''),
                '買賣': '買進' if o.get('action') == 'buy' else '賣出',
                '委託數量': o.get('quantity', 0),
                '成交數量': o.get('filled_quantity', 0),
                '成交均價': o.get('avg_fill_price', 0),
                '委託類型': '市價' if o.get('order_type') == 'market' else '限價',
                '委託價': o.get('price', 0),
                '委託金額': o.get('quantity', 0) * o.get('avg_fill_price', 0),
                '手續費': o.get('commission', 0),
                '證交稅': o.get('tax', 0),
                '狀態': o.get('status', ''),
                '委託單號': o.get('order_id', ''),
            }
            for o in filled
        ]

    # ==================== 實盤模式增強功能 ====================

    def is_live_mode(self) -> bool:
        """檢查是否為實盤模式"""
        return self.trader.mode == 'live'

    def get_account_info(self) -> dict:
        """取得帳戶資訊"""
        if hasattr(self.trader, 'get_account_info'):
            return self.trader.get_account_info()
        return {}

    def get_live_trades(self, date: str = None) -> list[dict]:
        """實盤：取得成交記錄"""
        if hasattr(self.trader, 'get_live_trades'):
            return self.trader.get_live_trades(date)
        return []

    def subscribe_trade_callback(self, callback) -> None:
        """實盤：設定交易回調（成交通知）"""
        if hasattr(self.trader, 'set_live_trade_callback'):
            self.trader.set_live_trade_callback(callback)

    def refresh_positions_live(self) -> list[dict]:
        """實盤：重新取得持股（從券商同步）"""
        return self.trader.get_positions()

    def refresh_balance_live(self) -> dict:
        """實盤：重新取得帳戶餘額（從券商同步）"""
        return self.trader.get_balance()


# 全域單例 - 委託給 app.py 的共用工廠
_order_manager: Optional[OrderManager] = None


def get_order_manager(trader: Optional[SinoPacTrader] = None) -> OrderManager:
    """取得訂單管理器實例 - 委託給 app.py 的 get_shared_order_manager"""
    from app import get_shared_order_manager as _get_shared
    return _get_shared()