# -*- coding: utf-8 -*-
from datetime import datetime, time
from math import sqrt
from alunir.main.base.bitflyer.strategy import Strategy
from alunir.main.base.common.indicator import *


no_trade_time_range = [
    (time( 7,55), time( 8, 5)), # JST 16:55-17:05
    (time( 8,55), time( 9, 5)), # JST 17:55-18:05
    (time( 9,55), time(10, 5)), # JST 18:55-19:05
    (time(10,55), time(11, 5)), # JST 19:55-20:05
    (time(11,55), time(12, 5)), # JST 20:55-21:05
    (time(12,55), time(13, 5)), # JST 21:55-22:05
    (time(13,55), time(14, 5)), # JST 22:55-23:05
    (time(14,55), time(15, 5)), # JST 23:55-00:05
    (time(15,55), time(23, 5)), # JST 00:55-08:05
    # (time(18,55), time(19, 55)), # JST 03:55-04:55 Bitflyerメンテナンスタイム
]


def stdev(src):
    average = sum(src) / len(src)
    average_sq = sum(p**2 for p in src) / len(src)
    var = average_sq - (average * average)
    dev = sqrt(var)
    return dev


def zscore(source):
    average = sum(source)/len(source)
    average_sq = sum(p**2 for p in source) / len(source)
    variance = average_sq - (average * average)
    std = sqrt(variance)
    return (source[-1]-average)/std if std else 0


class simple_market_maker:

    def __init__(self):
        pass

    def loop(self, ohlcv, ticker, strategy, **other):

        # メンテナンス時刻
        t = datetime.utcnow().time()
        coffee_break = False
        for s, e in no_trade_time_range:
            if t >= s and t <= e:
                strategy.logger.info('Coffee break ...')
                coffee_break = True
                break

        # エントリー
        if not coffee_break:
            # 遅延評価
            dist = ohlcv.distribution_delay[-3:]
            delay = sorted(dist)[int(len(dist)/2)]

            # 指値幅計算
            spr = max(stdev(ohlcv.close), 200)
            pairs = [(0.02, spr*0.75, '3', 14.5), (0.02, spr*0.5, '2', 9.5), (0.02, spr*0.25, '1', 4.5)]
            # pairs = [(0.03, spr*0.5, '2', 4.5), (0.03, spr*0.25, '1', 4.5)]
            maxsize = sum(p[0] for p in pairs)
            buymax = sellmax = strategy.position_size
            mid = (ohlcv.high[-1]+ohlcv.low[-1]+ohlcv.close[-1])/3
            z = zscore(ohlcv.volume_imbalance)
            ofs = z*9

            if delay>2.0:
                # if strategy.position_size>=0.01:
                #     strategy.order('L close', 'sell', qty=0.01)
                # elif strategy.position_size<=-0.01:
                #     strategy.order('S close', 'buy', qty=0.01)
                for _, _,suffix,_ in pairs:
                    strategy.cancel('L'+suffix)
                    strategy.cancel('S'+suffix)
            else:
                strategy.cancel('L close')
                strategy.cancel('S close')
                for size, width, suffix, period in pairs:
                    if buymax+size <= maxsize:
                        strategy.order('L'+suffix, 'buy', qty=size, limit=int(mid-width+ofs),
                            seconds_to_keep_order=period, minute_to_expire=1)
                        buymax += size
                    else:
                        strategy.cancel('L'+suffix)
                    if sellmax-size >= -maxsize:
                        strategy.order('S'+suffix, 'sell', qty=size, limit=int(mid+width+ofs),
                            seconds_to_keep_order=period, minute_to_expire=1)
                        sellmax -= size
                    else:
                        strategy.cancel('S'+suffix)
        else:
            strategy.cancel_order_all()
            strategy.close_position()


if __name__ == "__main__":
    from . import settings

    strategy = Strategy(simple_market_maker().loop, 5)
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.settings.max_ohlcv_size = 12*20
    strategy.settings.disable_rich_ohlcv = True
    strategy.risk.max_position_size = 0.06
    strategy.start()
