# -*- coding: utf-8 -*-
"""
永豐券商 API 包裝器
支援模擬交易模式和實盤交易模式
"""

from __future__ import annotations

import json
import os
import socket
import uuid
from datetime import datetime
from typing import Optional

from config import CONFIG

# 嘗試導入 shioaji，若無則標記為不可用
try:
    import shioaji as sj
    SHIOAJI_AVAILABLE = True
except ImportError:
    SHIOAJI_AVAILABLE = False


class SinoPacAPIError(Exception):
    """API 錯誤"""
    pass


class SinoPacTrader:
    """
    永豐券商交易 API
    mode='simulate'  : 模擬交易（無需 API Key）
    mode='live'      : 實盤交易（需要 shioaji 登入）
    """

    def __init__(
        self,
        mode: str = 'simulate',
        account_id: str = '',
        api_key: str = '',
        api_secret: str = '',
    ):
        self.config = CONFIG['trading']
        self.mode = mode or self.config.get('mode', 'simulate')
        self.account_id = account_id or self.config.get('account_id', '')
        self.api_key = api_key or self.config.get('api_key', '')
        self.api_secret = api_secret or self.config.get('api_secret', '')

        self._client = None
        self._orders: list[dict] = []
        self._positions: dict[str, dict] = {}
        self._balance: dict = {}
        self._ca_activated = False  # CA 憑證是否已啟用
        self._ca_path = self.config.get('ca_path', '')
        self._ca_passwd = self.config.get('ca_password', '')
        # 確保路徑使用正確的目錄
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._order_storage_path = os.path.join(base_dir, self.config.get('order_storage_path', 'trading/orders'))
        self._position_storage_path = os.path.join(base_dir, self.config.get('position_storage_path', 'trading/positions.json'))
        self._balance_storage_path = os.path.join(base_dir, self.config.get('balance_storage_path', 'trading/balance.json'))

        os.makedirs(self._order_storage_path, exist_ok=True)
        os.makedirs(os.path.dirname(self._balance_storage_path), exist_ok=True)
        self._load_orders()
        self._load_positions()
        self._load_balance_to_memory()

        if self.mode == 'live':
            if not self.api_key or not self.api_secret:
                raise SinoPacAPIError('實盤模式需要填寫 api_key 和 api_secret')
            self._init_live_client()

    def _load_balance_to_memory(self) -> None:
        """從檔案載入餘額到記憶體"""
        saved = self._load_balance()
        if saved:
            self._balance = saved
        else:
            # 沒有存檔，使用初始值
            self._reset_to_initial()

    def _init_balance(self) -> None:
        """初始化帳戶餘額"""
        self._reset_to_initial()

    def _reset_to_initial(self) -> None:
        """重置餘額為初始值"""
        initial_cash = self.config.get('simulate_initial_cash', 1000000)
        self._balance = {
            'cash': initial_cash,
            'initial_cash': initial_cash,
            'market_value': 0.0,
            'total_value': initial_cash,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
        }

    def _load_balance(self) -> dict | None:
        """從檔案載入帳戶餘額"""
        if os.path.exists(self._balance_storage_path):
            try:
                with open(self._balance_storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'cash' in data:
                        return data
            except Exception:
                pass
        return None

    def _init_live_client(self) -> None:
        """初始化實盤客戶端"""
        if not SHIOAJI_AVAILABLE:
            raise SinoPacAPIError('shioaji 套件未安裝，請執行: pip install shioaji')

        # 檢查網路連線
        try:
            socket.create_connection(("api.sinotrade.com.tw", 80), timeout=5)
        except OSError:
            raise SinoPacAPIError('無法連線到永豐伺服器，請檢查網路或防火牆設定')

        try:
            # 建立 Shioaji 實例
            self._client = sj.Shioaji(simulation=False)

            # 登入
            accounts = self._client.login(
                api_key=self.api_key,
                secret_key=self.api_secret,
            )

            if not accounts:
                raise SinoPacAPIError('登入成功但未取得任何帳號')

            # 設定使用指定帳號，或使用第一個可用帳號
            if self.account_id:
                for acc in self._client.list_accounts():
                    if str(acc.account_id) == str(self.account_id).strip():
                        self._account = acc
                        break
                else:
                    # 找不到指定帳號
                    all_accounts = self._client.list_accounts()
                    if all_accounts:
                        self._account = all_accounts[0]
                        print(f'警告：找不到指定帳號 {self.account_id}，使用預設帳號 {self._account.account_id}')
                    else:
                        raise SinoPacAPIError(f'找不到指定帳號 {self.account_id}，也沒有可用的備選帳號')
            else:
                # 未指定帳號，使用第一個
                all_accounts = self._client.list_accounts()
                if all_accounts:
                    self._account = all_accounts[0]
                else:
                    raise SinoPacAPIError('找不到可用的交易帳號')

            print(f'實盤登入成功，帳號：{self._account.account_id}')

        except SinoPacAPIError:
            raise
        except Exception as e:
            raise SinoPacAPIError(f'登入失敗：{e}')

    @property
    def client(self):
        """取得 shioaji 客戶端"""
        return self._client

    @property
    def account(self):
        """取得當前交易帳號"""
        return getattr(self, '_account', None)

    # ==================== 模擬模式核心邏輯 ====================

    def _reset_account(self) -> dict:
        """重置模擬帳戶（所有資料恢復初始狀態）"""
        # 重置餘額為初始值
        self._reset_to_initial()
        # 清空持股
        self._positions = {}
        # 清空委託
        self._orders = []
        # 清除所有存檔（讓下次載入時使用初始值）
        self._save_positions()
        self._save_orders()
        self._clear_balance_file()  # 關鍵：清除餘額檔案
        return self._balance

    def _clear_balance_file(self) -> None:
        """清除餘額檔案（重置時調用）"""
        try:
            if os.path.exists(self._balance_storage_path):
                os.remove(self._balance_storage_path)
        except Exception:
            pass

    def _calculate_commission(self, amount: float, is_buy: bool = True) -> float:
        """計算手續費"""
        rate = self.config.get('commission_rate', 0.00142)
        min_commission = self.config.get('min_commission', 20)
        commission = amount * rate
        return max(commission, min_commission)

    def _calculate_tax(self, amount: float) -> float:
        """計算證交稅（僅賣出時）"""
        rate = self.config.get('tax_rate', 0.003)
        return amount * rate

    def _simulate_fill(self, order: dict, current_price: float) -> dict:
        """
        模擬訂單成交
        市價單：立即以 current_price 成交
        限價單：若 current_price <= 委託價（買）或 >= 委託價（賣）則成交
        """
        order_type = order.get('order_type', 'market')
        action = order.get('action', 'buy')
        price = order.get('price', 0) or current_price
        quantity = order.get('quantity', 0)

        should_fill = False
        fill_price = current_price

        if order_type == 'market':
            should_fill = True
            fill_price = current_price
        elif order_type == 'limit':
            if action == 'buy' and current_price <= price:
                should_fill = True
                fill_price = price
            elif action == 'sell' and current_price >= price:
                should_fill = True
                fill_price = price

        if should_fill:
            return {
                'filled': True,
                'fill_price': fill_price,
                'fill_quantity': quantity,
                'fill_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        return {'filled': False, 'fill_price': 0, 'fill_quantity': 0, 'fill_time': None}

    def _update_position_after_trade(self, order: dict, fill_info: dict) -> None:
        """更新部位與現金"""
        if not fill_info.get('filled'):
            return

        code = order['code']
        action = order['action']
        fill_price = fill_info['fill_price']
        fill_quantity = fill_info['fill_quantity']

        if code not in self._positions:
            self._positions[code] = {
                'code': code,
                'name': order.get('name', code),
                'quantity': 0,
                'avg_cost': 0,
                'realized_pnl': 0,
            }

        pos = self._positions[code]

        # 計算交易成本
        trade_amount = fill_price * fill_quantity

        if action == 'buy':
            # 買進：扣除現金（含手續費）
            commission = self._calculate_commission(trade_amount, is_buy=True)
            total_cost = trade_amount + commission
            self._balance['cash'] -= total_cost

            # 更新持股
            total_value = pos['quantity'] * pos['avg_cost'] + fill_quantity * fill_price
            pos['quantity'] += fill_quantity
            pos['avg_cost'] = total_value / pos['quantity'] if pos['quantity'] > 0 else 0

        else:  # sell
            # 賣出：增加現金（扣手續費及證交稅）
            commission = self._calculate_commission(trade_amount, is_buy=False)
            tax = self._calculate_tax(trade_amount)
            net_proceeds = trade_amount - commission - tax
            self._balance['cash'] += net_proceeds

            # 計算已實現損益
            pnl = (fill_price - pos['avg_cost']) * fill_quantity
            pos['realized_pnl'] += pnl

            # 更新持股
            pos['quantity'] -= fill_quantity
            if pos['quantity'] <= 0:
                pos['quantity'] = 0
                pos['avg_cost'] = 0

        self._save_positions()
        self._save_balance()

    def _save_balance(self) -> None:
        """儲存帳戶餘額"""
        try:
            with open(self._balance_storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._balance, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _recalculate_balance(self, current_prices: dict = None) -> None:
        """重新計算帳戶餘額"""
        if current_prices is None:
            current_prices = {}

        market_value = 0.0
        unrealized_pnl = 0.0

        for code, pos in self._positions.items():
            if pos['quantity'] <= 0:
                continue
            price = current_prices.get(code, pos['avg_cost'])
            position_value = price * pos['quantity']
            market_value += position_value
            unrealized_pnl += (price - pos['avg_cost']) * pos['quantity']

        self._balance['market_value'] = market_value
        self._balance['unrealized_pnl'] = unrealized_pnl
        self._balance['total_value'] = self._balance['cash'] + market_value

    # ==================== 公開 API ====================

    def get_balance(self) -> dict:
        """取得帳戶餘額"""
        if self.mode == 'simulate':
            self._recalculate_balance()
            self._save_balance()  # 每次取得餘額時也更新存檔
            return self._balance.copy()
        else:
            return self._get_live_balance()

    def get_positions(self) -> list[dict]:
        """取得持有部位"""
        if self.mode == 'simulate':
            return [p for p in self._positions.values() if p.get('quantity', 0) > 0]
        else:
            return self._get_live_positions()

    def get_orders(self, date: str = None) -> list[dict]:
        """取得委託單"""
        if date:
            return [o for o in self._orders if o.get('trade_date', '').startswith(date)]
        return self._orders.copy()

    def get_order(self, order_id: str) -> dict | None:
        """取得特定委託單"""
        for order in self._orders:
            if order.get('order_id') == order_id:
                return order
        return None

    def place_order(
        self,
        code: str,
        quantity: int,
        action: str = 'buy',
        order_type: str = 'market',
        price: float = 0,
        name: str = '',
        current_price: float = 0,
    ) -> dict:
        """
        下單

        Args:
            code: 股票代碼
            quantity: 股數（需為1000的倍數）
            action: 'buy' 或 'sell'
            order_type: 'market' 或 'limit'
            price: 限價（order_type='limit' 時需要）
            name: 股票名稱
            current_price: 目前價格（模擬成交用）

        Returns:
            委託單資料
        """
        if quantity <= 0:
            raise SinoPacAPIError('數量必須大於 0')

        # 實盤模式：直接下單至券商
        if self.mode == 'live':
            return self._live_place_order(
                code=code,
                quantity=quantity,
                action=action,
                order_type=order_type,
                price=price,
                name=name,
            )

        # 模擬模式
        order_id = str(uuid.uuid4())[:8].upper()
        now = datetime.now()

        order = {
            'order_id': order_id,
            'trade_date': now.strftime('%Y-%m-%d'),
            'trade_time': now.strftime('%H:%M:%S'),
            'timestamp': now.isoformat(),
            'code': code,
            'name': name or code,
            'action': action,
            'order_type': order_type,
            'price': price,
            'quantity': quantity,
            'filled_quantity': 0,
            'avg_fill_price': 0,
            'status': 'pending',
            'filled_at': None,
        }

        if order_type in ('market', 'limit'):
            fill_info = self._simulate_fill(order, current_price)
            if fill_info['filled']:
                order['filled_quantity'] = fill_info['fill_quantity']
                order['avg_fill_price'] = fill_info['fill_price']
                order['status'] = 'filled'
                order['filled_at'] = fill_info['fill_time']
                # 這裡 _update_position_after_trade 已經處理了現金和手續費
                self._update_position_after_trade(order, fill_info)
                # 記錄費用（用於顯示，不重複扣款）
                order['commission'] = self._calculate_commission(fill_info['fill_quantity'] * fill_info['fill_price'], action == 'buy')
                if action == 'sell':
                    order['tax'] = self._calculate_tax(fill_info['fill_quantity'] * fill_info['fill_price'])
                else:
                    order['tax'] = 0

        self._orders.append(order)
        self._save_orders()

        # 重新計算總資產（傳入當前股價來計算市值）
        self._recalculate_balance({code: current_price or price or order.get('avg_fill_price', 0)})
        self._save_balance()  # 儲存更新後的餘額（含市值）
        return order

    def cancel_order(self, order_id: str) -> dict:
        """取消委託"""
        # 實盤模式
        if self.mode == 'live':
            return self._live_cancel_order(order_id)

        # 模擬模式
        for order in self._orders:
            if order.get('order_id') == order_id:
                if order['status'] in ('filled', 'cancelled'):
                    return {'success': False, 'message': f'委託狀態為 {order["status"]}，無法取消'}

                order['status'] = 'cancelled'
                order['cancelled_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._save_orders()
                return {'success': True, 'message': '委託已取消'}
        return {'success': False, 'message': '找不到委託單'}

    def modify_order(self, order_id: str, new_price: float = None, new_quantity: int = None) -> dict:
        """修改委託"""
        # 實盤模式
        if self.mode == 'live':
            return self._live_modify_order(order_id, new_price, new_quantity)

        # 模擬模式
        for order in self._orders:
            if order.get('order_id') == order_id:
                if order['status'] != 'pending':
                    return {'success': False, 'message': '僅可修改pending狀態的委託'}

                if new_price is not None:
                    order['price'] = new_price
                if new_quantity is not None:
                    order['quantity'] = new_quantity

                order['modified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._save_orders()
                return {'success': True, 'message': '委託已修改', 'order': order}
        return {'success': False, 'message': '找不到委託單'}

    # ==================== 實盤 API ====================

    def _get_live_balance(self) -> dict:
        """實盤：取得帳戶餘額"""
        if not self._client or not hasattr(self, '_account'):
            raise SinoPacAPIError('尚未登入實盤或無有效帳號')

        try:
            # 嘗試取得帳戶資金資料
            treasury = self._client.get_treasury(self._account)
            if treasury:
                balance = {
                    'cash': treasury.get('balance', 0) or treasury.get('available_balance', 0),
                    'initial_cash': 0,  # 實盤不追蹤初始資金
                    'market_value': 0,
                    'total_value': treasury.get('balance', 0) or treasury.get('available_balance', 0),
                    'realized_pnl': 0,
                    'unrealized_pnl': 0,
                    'fidelity': treasury.get('fidelity', 0),
                    'margin': treasury.get('margin', 0),
                    'raw_treasury': treasury,
                }
                return balance

            # 如果沒有 treasury，回傳基本資訊
            return {
                'cash': 0,
                'initial_cash': 0,
                'market_value': 0,
                'total_value': 0,
                'realized_pnl': 0,
                'unrealized_pnl': 0,
                'note': '無法取得帳戶餘額，可能需要檢查 API 權限',
            }
        except Exception as e:
            # 如果 API 调用失败，返回占位数据
            return {
                'cash': 0,
                'initial_cash': 0,
                'market_value': 0,
                'total_value': 0,
                'realized_pnl': 0,
                'unrealized_pnl': 0,
                'error': str(e),
            }

    def _get_live_positions(self) -> list[dict]:
        """實盤：取得持有部位"""
        if not self._client or not hasattr(self, '_account'):
            raise SinoPacAPIError('尚未登入實盤或無有效帳號')

        try:
            positions = self._client.get_position(self._account)
            if not positions:
                return []

            result = []
            for p in positions:
                # 處理不同的持股資料格式
                if hasattr(p, '__dict__'):
                    # shioaji 的 Position 物件
                    code = getattr(p, 'code', '') or getattr(p, 'stock_id', '')
                    name = getattr(p, 'name', '') or getattr(p, 'stock_name', '') or code
                    quantity = getattr(p, 'quantity', 0) or getattr(p, 'amount', 0)
                    avg_cost = getattr(p, 'unit_price', 0) or getattr(p, 'avg_price', 0) or getattr(p, 'purchase_price', 0)

                    result.append({
                        'code': str(code),
                        'name': str(name),
                        'quantity': int(quantity),
                        'avg_cost': float(avg_cost) if avg_cost else 0,
                        'realized_pnl': getattr(p, 'realized_pl', 0) or 0,
                        'unrealized_pnl': getattr(p, 'unrealized_pl', 0) or 0,
                        'raw_position': p.__dict__,
                    })
                elif isinstance(p, dict):
                    result.append({
                        'code': str(p.get('code', p.get('stock_id', ''))),
                        'name': str(p.get('name', p.get('stock_name', ''))),
                        'quantity': int(p.get('quantity', p.get('amount', 0))),
                        'avg_cost': float(p.get('unit_price', p.get('avg_price', p.get('purchase_price', 0))) or 0),
                        'realized_pnl': p.get('realized_pl', 0) or 0,
                        'unrealized_pnl': p.get('unrealized_pl', 0) or 0,
                    })

            return result
        except Exception as e:
            return []

    def _live_place_order(
        self,
        code: str,
        quantity: int,
        action: str,
        order_type: str,
        price: float,
        name: str,
    ) -> dict:
        """實盤下單"""
        if not self._client or not hasattr(self, '_account'):
            raise SinoPacAPIError('尚未登入實盤或無有效帳號')

        # 下單前檢查並啟用 CA 憑證（如需要）
        if not self._ca_activated:
            if self._ca_path and self._ca_passwd:
                try:
                    # CA 只需啟用一次，之後都有效
                    self._client.activate_ca(
                        ca_path=self._ca_path,
                        ca_passwd=self._ca_passwd,
                    )
                    self._ca_activated = True
                    print(f'CA 憑證啟用成功：{self._ca_path}')
                except Exception as e:
                    return {
                        'order_id': '',
                        'status': 'error',
                        'error': f'CA 憑證啟用失敗：{e}',
                        'code': code,
                        'name': name,
                        'action': action,
                        'message': '請確認 CA 憑證檔案路徑和密碼是否正確',
                    }
            else:
                # 沒有設定 CA，但可能可以下單（某些情況）
                print('警告：未設定 CA 憑證，若下單失敗請設定 ca_path 和 ca_password')

        try:
            # 取得股票合約
            contract = self._client.contract_stock(code)
            if not contract:
                raise SinoPacAPIError(f'找不到股票合約：{code}')

            # 建立訂單
            if action == 'buy':
                action_code = sj.constant.Action.Buy
            else:
                action_code = sj.constant.Action.Sell

            # 委託類型
            if order_type == 'market' or price <= 0:
                order_type_code = sj.constant.OrderType.MKO
            else:
                order_type_code = sj.constant.OrderType.LMT

            # 建立 Order 物件
            order = sj.Order(
                price=price if price > 0 else 0,
                quantity=quantity,
                action=action_code,
                order_type=order_type_code,
                price_type=sj.constant.TickVersion.Any if order_type == 'market' else sj.constant.TickVersion.LMT0,
                octype=sj.constant.Octype.New,
                account=self._account,
            )

            # 下單
            trade = self._client.place_order(self._account, contract, order)

            # 產生委託單號格式 (轉換 shioaji 回傳的格式)
            order_id = str(getattr(trade, 'order_id', getattr(trade, 'order_number', ''))) or str(uuid.uuid4())[:8].upper()

            return {
                'order_id': order_id,
                'trade_date': datetime.now().strftime('%Y-%m-%d'),
                'trade_time': datetime.now().strftime('%H:%M:%S'),
                'timestamp': datetime.now().isoformat(),
                'code': code,
                'name': name or code,
                'action': action,
                'order_type': order_type,
                'price': price,
                'quantity': quantity,
                'filled_quantity': getattr(trade, 'filled_quantity', 0) or 0,
                'avg_fill_price': getattr(trade, 'avg_fill_price', 0) or 0,
                'status': getattr(trade, 'status', 'submitted') or 'submitted',
                'filled_at': None,
                'is_live': True,
                'raw_trade': trade.__dict__ if hasattr(trade, '__dict__') else str(trade),
            }
        except Exception as e:
            return {
                'order_id': '',
                'status': 'error',
                'error': str(e),
                'code': code,
                'name': name,
                'action': action,
                'order_type': order_type,
                'price': price,
                'quantity': quantity,
                'message': f'下單失敗：{e}',
            }

    def _live_cancel_order(self, order_id: str) -> dict:
        """實盤取消委託"""
        if not self._client or not hasattr(self, '_account'):
            raise SinoPacAPIError('尚未登入實盤或無有效帳號')

        try:
            # 取得未成交委託
            open_orders = self._client.get_open_order(self._account)
            if not open_orders:
                return {'success': False, 'message': '無待成交委託'}

            # 找到要取消的委託
            target_order = None
            for o in open_orders:
                o_id = str(getattr(o, 'order_id', '') or getattr(o, 'order_number', ''))
                if o_id == order_id:
                    target_order = o
                    break

            if not target_order:
                return {'success': False, 'message': f'找不到委託單：{order_id}'}

            # 取消委託
            result = self._client.cancel_order(self._account, target_order)
            return {'success': True, 'message': '委託已取消', 'result': result}
        except Exception as e:
            return {'success': False, 'message': f'取消失敗：{e}'}

    def _live_modify_order(self, order_id: str, new_price: float = None, new_quantity: int = None) -> dict:
        """實盤修改委託"""
        if not self._client or not hasattr(self, '_account'):
            raise SinoPacAPIError('尚未登入實盤或無有效帳號')

        try:
            # 取得未成交委託
            open_orders = self._client.get_open_order(self._account)
            if not open_orders:
                return {'success': False, 'message': '無待修改委託'}

            # 找到要修改的委託
            target_order = None
            for o in open_orders:
                o_id = str(getattr(o, 'order_id', '') or getattr(o, 'order_number', ''))
                if o_id == order_id:
                    target_order = o
                    break

            if not target_order:
                return {'success': False, 'message': f'找不到委託單：{order_id}'}

            # 建立修改後的新訂單
            new_kwargs = {}
            if new_price is not None:
                new_kwargs['price'] = new_price
            if new_quantity is not None:
                new_kwargs['quantity'] = new_quantity

            if not new_kwargs:
                return {'success': False, 'message': '未提供修改內容'}

            # 執行修改
            result = self._client.update_order(self._account, target_order, **new_kwargs)
            return {'success': True, 'message': '委託已修改', 'result': result}
        except Exception as e:
            return {'success': False, 'message': f'修改失敗：{e}'}

    def get_live_trades(self, date: str = None) -> list[dict]:
        """實盤：取得成交記錄"""
        if not self._client or not hasattr(self, '_account'):
            return []

        try:
            trades = self._client.get_account_trades(self._account)
            if not trades:
                return []

            result = []
            for t in trades:
                if hasattr(t, '__dict__'):
                    result.append({
                        'code': getattr(t, 'code', ''),
                        'name': getattr(t, 'name', ''),
                        'action': 'buy' if getattr(t, 'action', '') == sj.constant.Action.Buy else 'sell',
                        'quantity': getattr(t, 'quantity', 0),
                        'price': getattr(t, 'price', 0),
                        'date': getattr(t, 'date', ''),
                        'time': getattr(t, 'time', ''),
                        'raw': t.__dict__,
                    })
                elif isinstance(t, dict):
                    result.append(t)

            # 過濾日期
            if date:
                result = [r for r in result if str(r.get('date', '')).startswith(date)]

            return result
        except Exception:
            return []

    def set_live_trade_callback(self, callback) -> None:
        """設定實盤交易回調（成交通知）"""
        if self._client and hasattr(self, '_account'):
            self._client.set_order_callback(callback)

    def get_account_info(self) -> dict:
        """取得帳戶資訊"""
        if not hasattr(self, '_account'):
            return {}
        acc = self._account
        return {
            'account_id': str(getattr(acc, 'account_id', '')),
            'username': getattr(acc, 'username', ''),
            'branch_id': getattr(acc, 'branch_id', ''),
            'account_type': getattr(acc, 'account_type', ''),
        }

    # ==================== 持久化 ====================

    def _load_orders(self) -> None:
        """載入委託記錄"""
        if os.path.exists(self._order_storage_path):
            try:
                with open(self._order_storage_path, 'r', encoding='utf-8') as f:
                    self._orders = json.load(f)
            except Exception:
                self._orders = []

    def _save_orders(self) -> None:
        """儲存委託記錄"""
        try:
            with open(self._order_storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._orders, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_positions(self) -> None:
        """載入部位"""
        if os.path.exists(self._position_storage_path):
            try:
                with open(self._position_storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._positions = data.get('positions', {})
            except Exception:
                self._positions = {}

    def _save_positions(self) -> None:
        """儲存部位"""
        try:
            data = {
                'updated_at': datetime.now().isoformat(),
                'positions': self._positions,
            }
            with open(self._position_storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def reset_account(self) -> dict:
        """重置帳戶（僅模擬模式）"""
        if self.mode != 'simulate':
            return {'success': False, 'message': '僅模擬模式可用'}
        return {'success': True, 'balance': self._reset_account()}

    def get_trade_summary(self) -> dict:
        """取得交易摘要"""
        orders = self._orders
        filled = [o for o in orders if o.get('status') == 'filled']
        buy_count = len([o for o in filled if o.get('action') == 'buy'])
        sell_count = len([o for o in filled if o.get('action') == 'sell'])

        total_commission = sum(o.get('commission', 0) for o in filled)
        total_tax = sum(o.get('tax', 0) for o in filled)

        return {
            'total_orders': len(orders),
            'filled_orders': len(filled),
            'pending_orders': len([o for o in orders if o.get('status') == 'pending']),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'total_commission': total_commission,
            'total_tax': total_tax,
        }


# 全域單例 - 確保只有一個 Trader 實例
_trader_instance: Optional[SinoPacTrader] = None


def get_trader(mode: str = 'simulate') -> SinoPacTrader:
    """取得交易實例（全域單例）"""
    global _trader_instance
    if _trader_instance is None:
        _trader_instance = SinoPacTrader(mode=mode)
    return _trader_instance


def reset_trader() -> None:
    """重置交易實例（用於測試或切换模式）"""
    global _trader_instance
    _trader_instance = None