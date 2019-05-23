# -*- coding: utf-8 -*-
from alunir.main.base.coincheck.strategy import Strategy
from alunir.main.base.common.strategy import StrategyBase


class Twap(StrategyBase):

    def use(self, strategy):
        pass

    def bizlogic(self, ohlcv, ticker, position, balance, execution, strategy, **other):
        strategy.entry('B', 'buy', strategy.settings.lot)
        strategy.logger.info("Wait %s seconds..." % strategy.settings.interval)


if __name__ == "__main__":
    strategy = Strategy(Twap)
    strategy.start()
