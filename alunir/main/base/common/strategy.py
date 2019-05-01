# -*- coding: utf-8 -*-
from abc import abstractmethod
from xross_common.DesignPattern import Singleton


class StrategyBase(Singleton):
    @abstractmethod
    def bizlogic(self, ohlcv, ticker, position, balance, executions, strategy, **other):
        pass
