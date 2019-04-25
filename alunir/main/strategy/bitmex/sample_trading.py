# -*- coding: utf-8 -*-
from alunir.main.base.bitmex.strategy import Strategy
from alunir.main.base.bitmex.indicator import *


def mylogic(ticker, ohlcv, position, balance, strategy):
    pass


if __name__ == '__main__':
    from . import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('sample_trading.log'))
    logger = logging.getLogger('SampleBot')

    strategy = Strategy(mylogic)
    strategy.settings.timeframe = '1m'
    strategy.settings.interval = 10
    strategy.testnet.use = True
    strategy.testnet.apiKey = settings.testnet_apiKey
    strategy.testnet.secret = settings.testnet_secret
    strategy.start()
