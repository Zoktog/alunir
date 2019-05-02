# -*- coding: utf-8 -*-
from alunir.main.base.bitmex.strategy import Strategy
from alunir.main.base.common.indicator import *
from alunir.main.base.common.strategy import StrategyBase

length = 20
multi = 2


class BbandStrategy(StrategyBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass

    def use(self, *args):
        pass

    def bizlogic(self, ohlcv, ticker, position, balance, executions, strategy, **other):
        # インジケーター作成
        source = ohlcv.close
        basis = sma(source, length)
        dev = multi * stdev(source, length)
        upper = basis + dev
        lower = basis - dev

        # エントリー・エグジット
        buyEntry = crossover(source, lower)
        sellEntry = crossunder(source, upper)
        strategy.logger.info('Lower ' + str(last(lower)) + ' Upper ' + str(last(upper)))

        # ロット数計算
        qty_lot = int(balance.BTC.free * 0.01 * ticker.last)

        # 最大ポジション数設定
        strategy.risk.max_position_size = qty_lot

        # 注文（ポジションがある場合ドテン）
        if last(buyEntry):
          strategy.entry('L', 'buy', qty=qty_lot, limit=ticker.bid)
        else:
          strategy.cancel('L')
        if last(sellEntry):
          strategy.entry('S', 'sell', qty=qty_lot, limit=ticker.ask)
        else:
          strategy.cancel('S')


if __name__ == "__main__":
    strategy = Strategy(BbandStrategy)
    strategy.start()
