# -*- coding: utf-8 -*-
import datetime
from alunir.main.base.bitflyer.strategy import Strategy
from alunir.main.base.common.indicator import *
from math import floor, ceil


def qround(n, q=1):
    return int(n // q * q)


def doten(position, lot):
    return lot * 2 if position > lot else lot+position


def flooring(price, q=100):
    return int(floor(price/q)*q)


def ceiling(price, q=100):
    return int(ceil(price/q)*q)


no_trade_time_range = [
    # (datetime.time( 7,55), datetime.time( 8, 5)), # JST 16:55-17:05
    # (datetime.time( 8,55), datetime.time( 9, 5)), # JST 17:55-18:05
    # (datetime.time( 9,55), datetime.time(10, 5)), # JST 18:55-19:05
    # (datetime.time(10,55), datetime.time(11, 5)), # JST 19:55-20:05
    # (datetime.time(11,55), datetime.time(12, 5)), # JST 20:55-21:05
    # (datetime.time(12,55), datetime.time(13, 5)), # JST 21:55-22:05
    # (datetime.time(13,55), datetime.time(14, 5)), # JST 22:55-23:05
    # (datetime.time(14,55), datetime.time(15, 5)), # JST 23:55-00:05
    # (datetime.time(15,55), datetime.time(23, 5)), # JST 01:00-08:05
    (datetime.time(18, 55), datetime.time(19, 55)), # JST 03:55-04:55 Bitflyerメンテナンスタイム
]


class mmbot:
    wait = 0
    n = 0
    maxslots = 1

    def __init__(self):
        self.wait = 0
        self.n = 0
        self.maxslots = 1

    def bizlogic(self, ohlcv, ticker, position, balance, executions, strategy, **other):

        self.n += 1
        if self.wait < 3:
            self.wait += 1
            return

        bid = ticker.best_bid
        ask = ticker.best_ask
        ltp = ticker.ltp
        mid = int((ask + bid) / 2)
        spr = ask - bid

        # 指値計算
        spread = int(max(stdev(ohlcv.close,17)[-1],110))
        limit_buy = flooring(ltp - spread)+3
        limit_sell = ceiling(ltp + spread)-3

        # トレンド指標計算
        vol = ohlcv.volume[-1]
        volma1 = sma(ohlcv.volume, 6)[-1]
        volma2 = sma(ohlcv.volume, 12)[-1]
        volimb = sma(ohlcv.volume_imbalance, 6)[-1]

        # 情報表示
        strategy.logger.info(
            'vol %.1f/%.1f/%.1f bid/ask %f/%f(%f) buy/sell %f/%f/%f'
            % (vol, volma1, volma2, bid, ask, spr, limit_buy, limit_sell, spread)
        )

        # 休憩時間（コーヒーでも飲んでまったりする）
        t = datetime.datetime.utcnow().time()
        coffee_break = False
        for s, e in no_trade_time_range:
            if t >= s and t <= e:
                strategy.logger.info('Coffee break ...')
                coffee_break = True
                break

        # エントリー
        if not coffee_break:

            # ロット調整
            qty_lot = 0.05

            # ポジションサイズ
            position_size = strategy.position_size

            # トレンド発生
            if volma1>100 or volma2>100 or vol>150:
                for no in range(self.maxslots):
                    strategy.cancel('L'+str(no))
                    strategy.cancel('S'+str(no))
                # ドテン
                if volimb>0:
                    strategy.order('Ltf', 'buy', qty=qty_lot)
                elif volimb<0:
                    strategy.order('Stf', 'sell', qty=qty_lot)
            else:
                # 利確指値
                if position_size > 0:
                    limit_buy = flooring(limit_buy-spread*0.333)+3
                    limit_sell = ceiling(limit_sell-spread*0.333)-3
                    if (bid - strategy.position_avg_price) >= spread*0.666:
                        limit_sell = bid
                elif position_size < 0:
                    limit_buy = flooring(limit_buy+spread*0.333)+3
                    limit_sell = ceiling(limit_sell+spread*0.333)-3
                    if (strategy.position_avg_price - ask) >= spread*0.666:
                        limit_buy = ask

                # 分割注文
                no = self.n%self.maxslots
                buysize = sellsize = qty_lot
                # if strategy.position_size < 0:
                #     buysize = buysize + -strategy.position_size
                # if strategy.position_size > 0:
                #     sellsize = sellsize + strategy.position_size
                o = strategy.get_order('L'+str(no))
                if o.status != 'open' or abs(o.price - limit_buy)>spread*0.111:
                    strategy.order('L'+str(no), 'buy', qty=buysize/self.maxslots, limit=min(limit_buy, bid-1), minute_to_expire=1)

                o = strategy.get_order('S'+str(no))
                if o.status != 'open' or abs(o.price - limit_sell)>spread*0.111:
                    strategy.order('S'+str(no), 'sell', qty=sellsize/self.maxslots, limit=max(limit_sell, ask+1), minute_to_expire=1)

                # 注文キャンセル完了してから次の注文を出す
                # # if o.status == 'open':
                # #     if abs(o.price - limit_buy)>spread*0.333:
                # #         strategy.cancel('L')
                # # elif o.status == 'closed' or o.status == 'canceled':
                # #     strategy.order('L', 'buy', qty=qty_lot, limit=min(limit_buy, bid-1), minute_to_expire=1)
                # # if o.status == 'open':
                # #     if abs(o.price - limit_sell)>spread*0.333:
                # #         strategy.cancel('S')
                # # elif o.status == 'closed' or o.status == 'canceled':
                # #     strategy.order('S', 'sell', qty=qty_lot, limit=max(limit_sell, ask+1), minute_to_expire=1)

        else:
            for no in range(self.maxslots):
                strategy.cancel('L'+str(no))
                strategy.cancel('S'+str(no))
            if strategy.position_size > 0:
                strategy.order('L close', 'sell', qty=strategy.position_size)
            elif strategy.position_size < 0:
                strategy.order('S close', 'buy', qty=-strategy.position_size)


if __name__ == "__main__":
    strategy = Strategy(mmbot)
    strategy.settings.show_last_n_orders = 10
    strategy.risk.max_position_size = 0.05
    strategy.start()
