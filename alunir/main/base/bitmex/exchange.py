# -*- coding: utf-8 -*-
import ccxt
from time import sleep
import pandas as pd
from datetime import datetime, timedelta
from tuned_bitmex_websocket.tuned_bitmex_websocket import BitMEXWebsocket
from alunir.main.base.common.order import OrderManager
from xross_common.Dotdict import Dotdict
from xross_common.SystemEnv import SystemEnv
from xross_common.SystemLogger import SystemLogger

RESAMPLE_INFO = {
    '1m': {'binSize': '1m', 'resample': False, 'count': 100, 'delta': timedelta(minutes=1)},
    '3m': {'binSize': '1m', 'resample': True, 'count': 120, 'delta': timedelta(minutes=1)},
    '5m': {'binSize': '5m', 'resample': False, 'count': 100, 'delta': timedelta(minutes=5)},
    '15m': {'binSize': '5m', 'resample': True, 'count': 120, 'delta': timedelta(minutes=5)},
    '30m': {'binSize': '5m', 'resample': True, 'count': 120, 'delta': timedelta(minutes=5)},
    '45m': {'binSize': '5m', 'resample': True, 'count': 120, 'delta': timedelta(minutes=5)},
    '1h': {'binSize': '1h', 'resample': False, 'count': 200, 'delta': timedelta(hours=1)},
    '2h': {'binSize': '1h', 'resample': True, 'count': 100, 'delta': timedelta(hours=1)},
    '4h': {'binSize': '1h', 'resample': True, 'count': 100, 'delta': timedelta(hours=1)},
    '1d': {'binSize': '1d', 'resample': False, 'count': 100, 'delta': timedelta(days=1)},
}


def excahge_error(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        for retry in range(0, 30):
            try:
                return func(*args, **kwargs)
            except ccxt.DDoSProtection as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 5
            except ccxt.RequestTimeout as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 5
            except ccxt.ExchangeNotAvailable as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 20
            except ccxt.AuthenticationError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                break
            except ccxt.ExchangeError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                waitsec = 3
            sleep(waitsec)
        raise Exception('Exchange Error Retry Timedout!!!')
    return wrapper


class Exchange:
    env = SystemEnv.create()
    logger, test_handler = SystemLogger(__name__).get_logger()

    def __init__(self, settings, apiKey='', secret=''):
        self.settings = settings

        self.apiKey = apiKey
        self.secret = secret

        # 注文管理
        self.om = None

        # 取引所情報
        self.exchange = None

        # ステータス
        self.running = False

        # WebSocket
        self.settings.use_websocket = False
        self.ws = None

    def start(self):
        self.running = True

        # 取引所セットアップ
        self.exchange = getattr(ccxt, self.settings.exchange)({
            'apiKey': self.settings.apiKey,
            'secret': self.settings.secret,
        })
        if self.env.is_real():
            self.logger.info('Start Exchange')
        else:
            self.exchange.urls['api'] = self.exchange.urls['test']
            self.logger.info('Start Test Exchange')
        self.exchange.load_markets()

        # マーケット一覧表示
        for k, v in self.exchange.markets.items():
            self.logger.info('Markets: ' + v['symbol'])

        # マーケット情報表示
        market = self.exchange.market(self.settings.symbol)
        self.logger.info('{symbol}: base:{base}'.format(**market))
        self.logger.info('{symbol}: quote:{quote}'.format(**market))
        self.logger.info('{symbol}: active:{active}'.format(**market))
        self.logger.info('{symbol}: taker:{taker}'.format(**market))
        self.logger.info('{symbol}: maker:{maker}'.format(**market))
        self.logger.info('{symbol}: type:{type}'.format(**market))

        self.om = OrderManager()

    def fetch_ticker(self, symbol=None, timeframe=None):
        symbol = symbol or self.settings.symbol
        timeframe = timeframe or self.settings.timeframe
        book = self.exchange.fetch_order_book(symbol, limit=1)
        trade = self.exchange.fetch_trades(symbol, limit=1, params={"reverse": True})
        ticker = Dotdict()
        ticker.bid = book['bids'][0][0]
        ticker.ask = book['asks'][0][0]
        ticker.last = trade[0]['price']
        ticker.datetime = pd.to_datetime(trade[0]['datetime'])
        self.logger.info("TICK: bid {bid} ask {ask} last {last}".format(**ticker))
        return ticker

    def fetch_ticker_ws(self):
        trade = self.ws.recent_trades()[-1]
        ticker = Dotdict(self.ws.get_ticker())
        ticker.datetime = pd.to_datetime(trade['timestamp'])
        self.logger.info("TICK: bid {bid} ask {ask} last {last}".format(**ticker))
        return ticker

    def fetch_ohlcv(self, symbol=None, timeframe=None):
        """過去100件のOHLCVを取得"""
        symbol = symbol or self.settings.symbol
        timeframe = timeframe or self.settings.timeframe
        partial = 'true' if self.settings.partial else 'false'
        rsinf = RESAMPLE_INFO[timeframe]
        market = self.exchange.market(symbol)
        req = {
            'symbol': market['id'],
            'binSize': rsinf['binSize'],
            'count': rsinf['count'],
            'partial': partial,     # True == include yet-incomplete current bins
            'reverse': 'false',
            'startTime': datetime.utcnow() - (rsinf['delta'] * rsinf['count']),
        }
        res = self.exchange.publicGetTradeBucketed(req)
        df = pd.DataFrame(res)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        if rsinf['resample']:
            rule = timeframe
            rule = rule.replace('m','T')
            rule = rule.replace('d','D')
            df = df.resample(rule=rule, closed='right').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        self.logger.info("OHLCV: {open} {high} {low} {close} {volume}".format(**df.iloc[-1]))
        return df

    def fetch_position(self, symbol=None):
        """現在のポジションを取得"""
        symbol = symbol or self.settings.symbol
        res = self.exchange.privateGetPosition()
        pos = [x for x in res if x['symbol'] == self.exchange.market(symbol)['id']]
        if len(pos):
            pos = Dotdict(pos[0])
            pos.timestamp = pd.to_datetime(pos.timestamp)
        else:
            pos = Dotdict()
            pos.currentQty = 0
            pos.avgCostPrice = 0
            pos.unrealisedPnl = 0
            pos.unrealisedPnlPcnt = 0
            pos.realisedPnl = 0
        pos.unrealisedPnlPcnt100 = pos.unrealisedPnlPcnt * 100
        self.logger.info("POSITION: qty {currentQty} cost {avgCostPrice} pnl {unrealisedPnl}({unrealisedPnlPcnt100:.2f}%) {realisedPnl}".format(**pos))
        return pos

    def fetch_position_ws(self):
        pos = Dotdict(self.ws.position())
        pos.unrealisedPnlPcnt100 = pos.unrealisedPnlPcnt * 100
        self.logger.info("POSITION: qty {currentQty} cost {avgCostPrice} pnl {unrealisedPnl}({unrealisedPnlPcnt100:.2f}%) {realisedPnl}".format(**pos))
        return pos

    def fetch_balance(self):
        """資産情報取得"""
        balance = Dotdict(self.exchange.fetch_balance())
        balance.BTC = Dotdict(balance.BTC)
        self.logger.info("BALANCE: free {free:.3f} used {used:.3f} total {total:.3f}".format(**balance.BTC))
        return balance

    def fetch_balance_ws(self):
        balance = Dotdict(self.ws.funds())
        balance.BTC = Dotdict()
        balance.BTC.free = balance.availableMargin * 0.00000001
        balance.BTC.total = balance.marginBalance * 0.00000001
        balance.BTC.used = balance.BTC.total - balance.BTC.free
        self.logger.info("BALANCE: free {free:.3f} used {used:.3f} total {total:.3f}".format(**balance.BTC))
        return balance

    def fetch_order(self, order_id):
        order = Dotdict({'status': 'closed', 'id': order_id})
        try:
            order = Dotdict(self.exchange.fetch_order(order_id))
            order.info = Dotdict(order.info)
        except ccxt.OrderNotFound as e:
            self.logger.warning(type(e).__name__ + ": {0}".format(e))
        return order

    def fetch_order_ws(self, order_id):
        orders = self.ws.all_orders()
        for o in orders:
            if o['orderID'] == order_id:
                order = Dotdict(self.exchange.parse_order(o))
                order.info = Dotdict(order.info)
                return order
        return Dotdict({'status':'closed', 'id':order_id})

    def create_order(self, symbol, type, side, qty, price, params):
        return self.exchange.create_order(symbol, type, side, qty, price=price, params=params)

    def edit_order(self, id, symbol, type, side, qty, price, params):
        return self.exchange.edit_order(id, symbol, type, side, amount=qty, price=price, params=params)

    @excahge_error
    def close_position(self, symbol=None):
        """現在のポジションを閉じる"""
        symbol = symbol or self.settings.symbol
        market = self.exchange.market(symbol)
        req = {'symbol': market['id']}
        res = self.exchange.privatePostOrderClosePosition(req)
        self.logger.info("CLOSE: {orderID} {side} {orderQty} {price}".format(**res))

    def cancel_order(self, myid):
        """注文をキャンセル"""
        open_orders = self.om.get_open_orders()
        if myid in open_orders:
            try:
                order_id = open_orders[myid].id
                res = self.exchange.cancel_order(order_id)
                self.logger.info("CANCEL: {orderID} {side} {orderQty} {price}".format(**res['info']))
            except ccxt.OrderNotFound as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
            except ccxt.NotFound as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
            # del open_orders[myid]
            self.om.cancel_order(myid)

    @excahge_error
    def cancel_order_all(self, symbol=None):
        """現在の注文をキャンセル"""
        symbol = symbol or self.settings.symbol
        market = self.exchange.market(symbol)
        req = {'symbol': market['id']}
        res = self.exchange.privateDeleteOrderAll(req)
        for r in res:
            self.logger.info("CANCEL: {orderID} {side} {orderQty} {price}".format(**r))

    def reconnect_websocket(self):
        # 再接続が必要がチェック
        need_reconnect = False
        if self.ws is None:
            need_reconnect = True
        else:
            if self.ws.connected == False:
                self.ws.exit()
                need_reconnect = True

        # 再接続
        if need_reconnect:
            market = self.exchange.market(self.settings.symbol)
            # ストリーミング設定
            if self.env.is_real():
                self.ws = BitMEXWebsocket(
                    endpoint='wss://www.bitmex.com',
                    symbol=market['id'],
                    api_key=self.settings.apiKey,
                    api_secret=self.settings.secret
                )
            else:
                self.ws = BitMEXWebsocket(
                    endpoint='wss://testnet.bitmex.com/realtime',
                    symbol=market['id'],
                    api_key=self.settings.apiKey,
                    api_secret=self.settings.secret
                )
            # ネットワーク負荷の高いトピックの配信を停止
            self.ws.unsubscribe(['orderBookL2'])
