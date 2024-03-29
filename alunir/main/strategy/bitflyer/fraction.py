# -*- coding: utf-8 -*-
from alunir.main.base.bitflyer.strategy import Strategy
from alunir.main.base.bitflyer.indicator import *
from math import floor, ceil, sqrt
from datetime import datetime, time

suspension_period = [
    (time(18, 55), time(19, 55)), # JST 03:55-04:55 Bitflyerメンテナンスタイム
]


def stdev(src):
    average = sum(src) / len(src)
    average_sq = sum(p**2 for p in src) / len(src)
    var = average_sq - (average * average)
    dev = sqrt(var)
    return dev


class fraction:

    def __init__(self):
        self.api_limit = 0

    def loop(self, ticker, ohlcv, strategy, **other):

        if self.api_limit:
            self.api_limit -= 1

        # メンテナンス時刻
        t = datetime.utcnow().time()
        coffee_break = False
        for s, e in suspension_period:
            if t >= s and t <= e:
                logger.info('Coffee break ...')
                coffee_break = True
                break

        if not coffee_break:

            # 遅延評価
            dist = ohlcv.distribution_delay[-11:]
            delay = sorted(dist)[int(len(dist)/2)]

            if delay<2:
                mid = (ohlcv.close[-1]+ohlcv.high[-1]+ohlcv.low[-1])/3
                spr = stdev(ohlcv.close)
                lot = 0.01
                rng = 51
                buy = ((mid-spr/2)//rng)*rng
                sell = ((mid+spr/2)//rng+1)*rng

                # 同じ価格に指値を入れない
                buy_prices = set([p['price'] for p in strategy.positions if p['side']=='buy'])
                sell_prices = set([p['price'] for p in strategy.positions if p['side']=='sell'])
                if buy not in buy_prices:
                    strategy.order('%s' % buy, 'buy', qty=lot, limit=buy, minute_to_expire=1)
                if sell not in sell_prices:
                    strategy.order('%s' % sell, 'sell', qty=lot, limit=sell, minute_to_expire=1)

                # 利確・損切り
                profit = rng
                loss = -rng*0.5
                for p in strategy.positions:
                    side, price, size = p['side'], p['price'], p['size']
                    if size >= lot:
                        if side == 'buy':
                            pnl = mid-price
                            if pnl <= loss or pnl >= profit:
                                strategy.order('C%f' % price, 'sell', qty=size)
                        else:
                            pnl = price-mid
                            if pnl <= loss or pnl >= profit:
                                strategy.order('C%f' % price, 'buy', qty=size)
            else:
                strategy.cancel_order_all()
                strategy.close_position()
        else:
            strategy.cancel_order_all()
            strategy.close_position()


if __name__ == "__main__":
    from . import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('fraction.log'))
    logger = logging.getLogger("fraction")

    strategy = Strategy(fraction().loop, 0.5)
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.settings.max_ohlcv_size = 30
    strategy.settings.disable_rich_ohlcv = True
    strategy.risk.max_position_size = 0.1
    strategy.start()
