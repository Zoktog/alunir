# -*- coding: utf-8 -*-
import ccxt
from time import sleep
import pandas as pd
from datetime import datetime, timedelta
from alunir.main.base.common.order import OrderManager
from xross_common.Dotdict import Dotdict
from xross_common.SystemEnv import SystemEnv
from xross_common.SystemLogger import SystemLogger
from oslash import Right, Left

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

RESAMPLE_INFO = {
    '1m': {'binSize': '1m', 'resample': False, 'count': 200, 'delta': timedelta(minutes=1)},
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
        # self.settings.use_websocket = False
        self.ws = None

        # TODO: safe_api_caller
        self.trades = None
        self.__last_timestamp_recent_trades = datetime(year=1970, month=1, day=1)

    def start(self):
        self.running = True

        # 取引所セットアップ
        self.exchange = getattr(ccxt, self.settings.exchange)({
            'apiKey': self.settings.apiKey,
            'secret': self.settings.secret,
        })
        self.exchange.nonce = ccxt.Exchange.milliseconds

        self.logger.info('Start Exchange')

        self.exchange.load_markets()

        # マーケット一覧表示
        for k, v in self.exchange.markets.items():
            self.logger.info('Markets: ' + v['symbol'])

        # マーケット情報表示
        market = self.exchange.market(self.settings.symbol)
        # self.logger.debug(market)
        self.logger.info('{symbol}: base:{base}'.format(**market))
        self.logger.info('{symbol}: quote:{quote}'.format(**market))
        # self.logger.info('{symbol}: active:{active}'.format(**market))
        self.logger.info('{symbol}: taker:{taker}'.format(**market))
        self.logger.info('{symbol}: maker:{maker}'.format(**market))
        # self.logger.info('{symbol}: type:{type}'.format(**market))

        self.om = OrderManager()

    def __safe_api_recent_trades(self, symbol, **params):
        if datetime.now() - self.__last_timestamp_recent_trades > timedelta(seconds=self.settings.interval):
            self.trades = self.exchange.fetch_trades(symbol, **params)
            self.__last_timestamp_recent_trades = datetime.fromtimestamp(int(self.trades[0]['id']))
        return self.trades

    def __safe_api_recent_trades_ws(self, **params):
        if datetime.now() - self.__last_timestamp_recent_trades > timedelta(seconds=self.settings.interval):
            self.trades = self.ws.recent_trades(**params)
            self.__last_timestamp_recent_trades = datetime.strptime(self.trades[0]['timestamp'], DATETIME_FORMAT)
        return self.trades

    def fetch_my_executions(self, symbol, orders, **params):
        trades = self.__safe_api_recent_trades(symbol, **params)
        order_ids = [v['id'] for myid, v in orders.items()]
        trade_ids = [trade['id'] for trade in trades]
        return [order_id for order_id in order_ids if order_id in trade_ids]

    def fetch_my_executions_ws(self, orders, **params):
        trades = self.__safe_api_recent_trades_ws(**params)
        order_ids = {{v['id']: myid} for myid, v in orders.items()}
        trade_ids = {trade['id'] for trade in trades}
        return [order_id for order_id in order_ids if order_id in trade_ids]

    def fetch_ticker(self, symbol=None, timeframe=None):
        symbol = symbol or self.settings.symbol
        timeframe = timeframe or self.settings.timeframe
        book = self.exchange.fetch_order_book(symbol, limit=10)
        trade = self.__safe_api_recent_trades(symbol, limit=1, params={"reverse": True})
        ticker = Dotdict()
        ticker.bid, ticker.bidsize = book['bids'][0]
        ticker.ask, ticker.asksize = book['asks'][0]
        ticker.bids = book['bids']
        ticker.asks = book['asks']
        ticker.last = trade[0]['price']
        ticker.datetime = pd.to_datetime(trade[0]['datetime'], utc=True).tz_convert('Asia/Tokyo')
        self.logger.info("TICK: bid {bid} ask {ask} last {last}".format(**ticker))
        self.logger.info("TRD: price {rate} size {amount} side {order_type} ".format(**(trade[0]['info'])))
        return ticker, trade

    def fetch_ticker_ws(self):
        trade = self.__safe_api_recent_trades_ws()[-1]
        ticker = Dotdict(self.ws.get_ticker())
        ticker.datetime = pd.to_datetime(trade['timestamp'])
        self.logger.info("TICK: bid {bid} ask {ask} last {last}".format(**ticker))
        self.logger.info("TRD: price {price} size {size} side {side} tick {tickDirection} ".format(**(trade['info'])))
        return ticker, trade

    def fetch_ohlcv(self, symbol=None, timeframe=None):
        """過去100件のOHLCVを取得"""
        symbol = symbol or self.settings.symbol
        timeframe = timeframe or self.settings.timeframe
        partial = 'true' if self.settings.partial else 'false'
        rsinf = RESAMPLE_INFO[timeframe]
        market = self.exchange.market(symbol)
        # req = {
        #     'symbol': market['id'],
        #     'binSize': rsinf['binSize'],
        #     'count': rsinf['count'],
        #     'partial': partial,     # True == include yet-incomplete current bins
        #     'reverse': 'false',
        #     'startTime': datetime.utcnow() - (rsinf['delta'] * rsinf['count']),
        # }
        res = self.exchange.fetchOHLCV(symbol=symbol, timeframe=timeframe, since=None, limit=rsinf['count'], params={'reverse': True})
        res2 = res.copy()
        for i in range(len(res)):
            res2[i][0] = datetime.fromtimestamp(int(res[i][0])/1000.0)
        del res
        keys = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        dict_res = [dict(zip(keys, r)) for r in res2]
        df = pd.DataFrame(dict_res).set_index('timestamp')
        self.logger.info("OHLCV: {open} {high} {low} {close} {volume}".format(**df.iloc[-1]))
        return df

    def fetch_position(self, symbol=None):
        """現在のポジションを取得"""
        # symbol = symbol or self.settings.symbol
        # res = self.exchange.fetchMyTrades(symbol=symbol)
        # self.logger.info("POSITION: qty {currentQty} cost {avgCostPrice} pnl {unrealisedPnl}({unrealisedPnlPcnt100:.2f}%) {realisedPnl}".format(**pos))
        # TODO: please implement someday
        return None

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
            order = Dotdict(self.exchange.parse_order(self.exchange.fetch_open_orders(order_id)))
            # order.info = Dotdict(order.info)
            order.status = 'open'
        except ccxt.OrderNotFound as e:
            self.logger.warning(type(e).__name__ + ": {0}".format(e))
        return order

    def fetch_order_ws(self, order_id):
        orders = self.ws.all_orders()
        for o in orders:
            if o['id'] == order_id:
                order = Dotdict(self.exchange.parse_order(o))
                order.info = Dotdict(order.info)
                return order
        return Dotdict({'status': 'closed', 'id': order_id})

    def create_order(self, myid, symbol, type, side, qty, price, params):
        self.logger.info(
            "Requesting to create a new order. symbol:%s, type:%s, side:%s, qty:%s, price:%s"
            % (symbol, type, side, qty, price)
        )
        try:
            result = Right(self.exchange.create_order(symbol, type, side, qty, price=price, params=params))

            order = Dotdict()
            order.myid = myid
            order.accepted_at = datetime.utcnow().strftime(DATETIME_FORMAT)
            order.id = result.value['info']['id']
            order.status = 'accepted'
            order.symbol = symbol
            order.type = type.lower()
            order.side = side
            order.price = price if price is not None else 0
            order.average_price = 0
            order.cost = 0
            order.amount = qty
            order.filled = 0
            order.remaining = 0
            order.fee = 0
            self.om.add_order(order)
        except ccxt.BadRequest as e:
            self.logger.warning("Returned BadRequest: %s" % str(e))
            result = Left("Returned BadRequest: %s" % str(e))
        except Exception as e:
            self.logger.warning("Returned Exception: %s" % str(e))
            result = Left(str(e))
        return result.value

    def edit_order(self, myid, symbol, type, side, qty, price, params):
        self.logger.info(
            "Requesting to amend the order. myid:%s, symbol:%s, type:%s, side:%s, qty:%s, price:%s"
            % (myid, symbol, type, side, qty, price)
        )

        try:
            active_order = self.om.get_open_order(myid)
            if active_order is None:
                self.logger.warning("No ActiveOrder exists.")
                return
            result = Right(self.exchange.edit_order(
                active_order.id, symbol, type, side, amount=qty, price=price, params=params
            ))

            active_order.myid = myid
            active_order.accepted_at = datetime.utcnow().strftime(DATETIME_FORMAT)
            active_order.id = result.value['info']['id']
            active_order.status = 'accepted'
            # order.symbol = symbol
            active_order.type = type.lower()
            # order.side = side
            active_order.price = price if price is not None else 0
            active_order.average_price = 0
            active_order.cost = 0
            active_order.amount = qty
            active_order.filled = 0  # FIXME
            active_order.remaining = 0  # FIXME
            active_order.fee = 0
            self.om.add_order(active_order)
        except ccxt.BadRequest as e:
            self.logger.warning("Returned BadRequest: %s" % str(e))
            result = Left("Returned BadRequest: %s" % str(e))
            self.om.cancel_order(myid)
        except Exception as e:
            self.logger.warning("Returned Exception: %s" % str(e))
            result = Left(str(e))
        return result.value

    @excahge_error
    def close_position(self, symbol=None):
        """現在のポジションを閉じる"""
        symbol = symbol or self.settings.symbol
        market = self.exchange.market(symbol)
        req = {'symbol': market['id']}
        res = self.exchange.privatePostOrderClosePosition(req)
        self.logger.info("CLOSE: {id} {order_type} {amount} {rate}".format(**res))

    def cancel_order(self, myid):
        """注文をキャンセル"""
        open_orders = self.om.get_open_orders()
        if myid in open_orders:
            try:
                details = open_orders[myid]
                self.logger.info(
                    "Requesting to cancel the order. myid:%s, id:%s, symbol:%s, type:%s, side:%s, qty:%s, price:%s"
                    % (myid, details.id, details.symbol, details.type, details.side, details.qty, details.price)
                )
                res = self.exchange.cancel_order(details.id)
                self.logger.info("CANCEL: {id} {order_type} {amount} {rate}".format(**res['info']))
            except ccxt.OrderNotFound as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
            except Exception as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
            # del open_orders[myid]
            self.om.cancel_order(myid)

    @excahge_error
    def cancel_order_all(self, symbol=None):
        """現在の注文をキャンセル"""
        symbol = symbol or self.settings.symbol
        res = self.exchange.fetch_open_orders(symbol=symbol)
        for r in res:
            self.logger.info("CANCEL: {id} {order_type} {amount} {rate}".format(**r))

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
            # if self.env.is_real():
            #     self.ws = BitMEXWebsocket(
            #         endpoint='wss://www.bitmex.com',
            #         symbol=market['id'],
            #         api_key=self.settings.apiKey,
            #         api_secret=self.settings.secret
            #     )
            # else:
            #     self.ws = BitMEXWebsocket(
            #         endpoint='wss://testnet.bitmex.com/realtime',
            #         symbol=market['id'],
            #         api_key=self.settings.apiKey,
            #         api_secret=self.settings.secret
            #     )
            # ネットワーク負荷の高いトピックの配信を停止
            self.ws.unsubscribe(['orderBookL2'])
