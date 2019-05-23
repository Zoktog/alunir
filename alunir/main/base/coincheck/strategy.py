# -*- coding: utf-8 -*-
from time import sleep

import ccxt
from xross_common.SystemLogger import SystemLogger
from xross_common.SystemUtil import SystemUtil
from xross_common.CustomErrors import BaseError

from alunir.main.base.coincheck.exchange import Exchange
from alunir.main.base.common.utils import Dotdict, validate


class OrderNotFoundException(BaseError):
    """"Raised when the order isn't found"""
    pass


class Strategy:
    cfg = SystemUtil(skip=True)

    def __init__(self, yourlogic):

        # ログ設定
        self.logger, self.test_handler = SystemLogger(yourlogic.__name__).get_logger()
        self.logger.info("Initializing Strategy...")

        # トレーディングロジック設定
        self.yourlogic = yourlogic

        # 取引所情報
        self.settings = Dotdict()
        self.settings.exchange = self.cfg.get_env("EXCHANGE", default='coincheck')
        self.settings.symbol = self.cfg.get_env("SYMBOL", default='BTC/JPY')
        self.settings.lot = int(self.cfg.get_env("LOT", default=1000))
        self.settings.use_websocket = self.cfg.get_env("USE_WEB_SOCKET", type=bool, default=True)
        self.logger.info("USE_WEB_SOCKET: %s" % self.settings.use_websocket)

        self.settings.apiKey = self.cfg.get_env("COINCHECK_KEY")
        self.settings.secret = self.cfg.get_env("COINCHECK_SECRET_KEY")

        self.settings.close_position_at_start_stop = False

        # 動作タイミング
        self.settings.interval = int(self.cfg.get_env("INTERVAL", default=86400))

        # ohlcv設定
        self.settings.timeframe = self.cfg.get_env("TIMEFRAME", default='1m')
        self.settings.partial = False

        # リスク設定
        self.risk = Dotdict()
        self.risk.max_position_size = 20000
        self.risk.max_drawdown = 200000

        # ポジション情報
        self.position = Dotdict()
        self.position.currentQty = 0

        # 資金情報
        self.balance = None

        # 注文情報
        self.orders = Dotdict()

        # ティッカー情報
        self.ticker = Dotdict()

        # ohlcv情報
        self.ohlcv = None
        self.ohlcv_updated = False

        # 約定情報
        self.executions = Dotdict()

        # 取引所接続
        self.exchange = Exchange(self.settings, apiKey=self.settings.apiKey, secret=self.settings.secret)

        self.logger.info("Completed to initialize Strategy.")

    def create_order(self, myid, side, qty, limit, stop, trailing_offset, symbol):
        type = 'market'
        params = {}
        if stop is not None and limit is not None:
            type = 'stopLimit'
            params['stopPx'] = stop
            params['execInst'] = 'LastPrice'
            # params['price'] = limit
        elif stop is not None:
            type = 'stop'
            params['stopPx'] = stop
            params['execInst'] = 'LastPrice'
        elif limit is not None:
            type = 'limit'
            # params['price'] = limit
        if trailing_offset is not None:
            params['pegPriceType'] = 'TrailingStopPeg'
            params['pegOffsetValue'] = trailing_offset
        symbol = symbol or self.settings.symbol
        res = self.exchange.create_order(myid, symbol, type, side, qty, limit, params)
        self.logger.info("ORDER: {id} {order_type} {amount} {rate}({stop_loss_rate})".format(**res['info']))
        return Dotdict(res)

    def edit_order(self, myid, side, qty, limit=None, stop=None, trailing_offset=None, symbol=None):
        type = 'market'
        params = {}
        if stop is not None and limit is not None:
            type = 'stopLimit'
            params['stopPx'] = stop
            # params['price'] = limit
        elif stop is not None:
            type = 'stop'
            params['stopPx'] = stop
        elif limit is not None:
            type = 'limit'
            # params['price'] = limit
        if trailing_offset is not None:
            params['pegOffsetValue'] = trailing_offset
        symbol = symbol or self.settings.symbol
        res = self.exchange.edit_order(myid, symbol, type, side, qty, limit, params)
        self.logger.info("EDIT: {id} {order_type} {amount} {rate}({stop_loss_rate})".format(**res['info']))
        return Dotdict(res)

    def order(self, myid, side, qty, limit=None, stop=None, trailing_offset=None, symbol=None):
        """注文"""

        qty_total = qty
        qty_limit = self.risk.max_position_size

        # # 買いポジあり
        # if self.position.currentQty > 0:
        #     # 買い増し
        #     if side == 'buy':
        #         # 現在のポジ数を加算
        #         qty_total = qty_total + self.position.currentQty
        #     else:
        #         # 反対売買の場合、ドテンできるように上限を引き上げる
        #         qty_limit = qty_limit + self.position.currentQty
        #
        # # 売りポジあり
        # if self.position.currentQty < 0:
        #     # 売りまし
        #     if side == 'sell':
        #         # 現在のポジ数を加算
        #         qty_total = qty_total + -self.position.currentQty
        #     else:
        #         # 反対売買の場合、ドテンできるように上限を引き上げる
        #         qty_limit = qty_limit + -self.position.currentQty

        # 購入数をポジション最大サイズに抑える
        if qty_total > qty_limit:
            qty = qty - (qty_total - qty_limit)

        if qty > 0:
            symbol = symbol or self.settings.symbol

            if myid in self.orders:
                order = self.exchange.fetch_order(self.orders[myid].id)

                # 未約定・部分約定の場合、注文を編集
                if order.status == 'open':
                    # オーダータイプが異なる or STOP注文がトリガーされたら編集に失敗するのでキャンセルしてから新規注文する
                    order_type = 'stop' if stop is not None else ''
                    order_type = order_type + 'limit' if limit is not None else order_type
                    if (order_type != order.type) or (order.type == 'stoplimit' and order.info.triggered == 'StopOrderTriggered'):
                        # 注文キャンセルに失敗した場合、ポジション取得からやり直す
                        self.exchange.cancel_order(myid)
                        order = self.create_order(myid, side, qty, limit, stop, trailing_offset, symbol)
                    else:
                        # 指値・ストップ価格・数量に変更がある場合のみ編集を行う
                        if ((order.info.price is not None and order.info.price != limit) or
                            (order.info.stopPx is not None and order.info.stopPx != stop) or
                            (order.info.orderQty is not None and order.info.orderQty != qty)):
                            order = self.edit_order(myid, side, qty, limit, stop, trailing_offset, symbol)

                # 約定済みの場合、新規注文
                else:
                    order = self.create_order(myid, side, qty, limit, stop, trailing_offset, symbol)

            # 注文がない場合、新規注文
            else:
                order = self.create_order(myid, side, qty, limit, stop, trailing_offset, symbol)

            self.orders[myid] = order

            return order

    def entry(self, myid, side, qty, limit=None, stop=None, trailing_offset=None, symbol=None):
        """注文"""

        # # 買いポジションがある場合、清算する
        # if side == 'sell' and self.position.currentQty > 0:
        #     qty = qty + self.position.currentQty
        #
        # # 売りポジションがある場合、清算する
        # if side == 'buy' and self.position.currentQty < 0:
        #     qty = qty - self.position.currentQty

        # qty validation
        price = limit or self.ticker.ask if side == 'buy' else self.ticker.bid
        if qty < price * 0.005:
            self.logger.warning("Quantity validation. Order quantity %s JPY (%s BTC) is lower than 0.005 BTC" % (qty, qty/price))
            return

        # 注文
        return self.order(myid, side, qty, limit=limit, stop=stop, trailing_offset=trailing_offset, symbol=symbol)

    def cancel(self, myid):
        return self.exchange.cancel_order(myid)

    def update_ohlcv(self, ticker_time=None, force_update=False):
        if self.settings.partial or force_update:
            self.ohlcv = self.exchange.fetch_ohlcv()
            self.ohlcv_updated = True
        else:
            # 次に足取得する時間
            timestamp = self.ohlcv.index
            t0 = timestamp[-1]
            t1 = timestamp[-2]
            next_fetch_time = t0 + (t0 - t1)
            # 足取得
            if ticker_time > next_fetch_time:
                self.ohlcv = self.exchange.fetch_ohlcv()
                # 更新確認
                timestamp = self.ohlcv.index
                if timestamp[-1] >= next_fetch_time:
                    self.ohlcv_updated = True

    def setup(self):
        validate(self, "self.settings.apiKey")
        validate(self, "self.settings.secret")

        self.exchange.start()

        self.yourlogic()
        args = {
            'strategy': self
        }
        self.yourlogic.use(self.yourlogic, **args)

    def add_arguments(self, parser):
        parser.add_argument('--apikey', type=str, default=self.settings.apiKey)
        parser.add_argument('--secret', type=str, default=self.settings.secret)
        parser.add_argument('--symbol', type=str, default=self.settings.symbol)
        parser.add_argument('--timeframe', type=str, default=self.settings.timeframe)
        parser.add_argument('--interval', type=float, default=self.settings.interval)
        return parser

    def start(self):
        self.logger.info("Setup Strategy")
        self.setup()

        # 全注文キャンセル
        self.exchange.cancel_order_all()

        # ポジションクローズ
        if self.settings.close_position_at_start_stop:
            self.exchange.close_position()

        self.logger.info("Start Trading")

        # 強制足取得
        self.update_ohlcv(force_update=True)

        errorWait = 0
        while True:
            try:
                # 例外発生時の待ち
                if errorWait:
                    sleep(errorWait)
                    errorWait = 0

                if self.settings.use_websocket:
                    # WebSocketの接続が切れていたら再接続
                    self.exchange.reconnect_websocket()

                    # ティッカー取得
                    self.ticker, last_execution = self.exchange.fetch_ticker_ws()

                    # ポジション取得
                    self.position = self.exchange.fetch_position_ws()

                    # 資金情報取得
                    self.balance = self.exchange.fetch_balance_ws()

                    # 約定情報
                    self.executions = self.exchange.fetch_my_executions_ws(self.orders)
                else:
                    # ティッカー取得
                    self.ticker, last_execution = self.exchange.fetch_ticker()

                    # ポジション取得
                    self.position = self.exchange.fetch_position()

                    # 資金情報取得
                    self.balance = self.exchange.fetch_balance()

                    # 約定情報
                    self.executions = self.exchange.fetch_my_executions(self.settings.symbol, self.orders)

                # 足取得（足確定後取得）
                self.update_ohlcv(ticker_time=self.ticker.datetime)

                # メインロジックコール
                arg = {
                    'strategy': self,
                    'ticker': self.ticker,
                    'ohlcv': self.ohlcv,
                    'position': self.position,
                    'balance': self.balance,
                    'execution': self.executions
                }
                self.yourlogic.bizlogic(self.yourlogic, **arg)

            except ccxt.DDoSProtection as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 30
            except ccxt.RequestTimeout as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 5
            except ccxt.ExchangeNotAvailable as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 20
            except ccxt.AuthenticationError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                break
            except ccxt.ExchangeError as e:
                self.logger.warning(type(e).__name__ + ": {0}".format(e))
                errorWait = 5
            except (KeyboardInterrupt, SystemExit):
                self.logger.info('Shutdown!')
                break
            except Exception as e:
                self.logger.exception(e)
                errorWait = 5

            # 通常待ち
            sleep(self.settings.interval)

        self.logger.info("Stop Trading")

        # 全注文キャンセル
        self.exchange.cancel_order_all()

        # ポジションクローズ
        if self.settings.close_position_at_start_stop:
            self.exchange.close_position()
