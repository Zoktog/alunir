# -*- coding: utf-8 -*-
from alunir.main.base.bitmex.strategy import Strategy
from alunir.main.base.common.strategy import StrategyBase
from xross_common.Dotdict import Dotdict

SPREAD = 1


class OrderImbalance(StrategyBase):
    qty = None

    def q(self, ticker_a, ticker_b):
        def qa(ticker_a, ticker_b):
            return min(ticker_a.asksize - ticker_b.asksize, 0) + max(ticker_a.bidsize - ticker_b.bidsize, 0)

        def qb(ticker_a, ticker_b):
            return min(ticker_a.bidsize - ticker_b.bidsize, 0) + max(ticker_a.asksize - ticker_b.asksize, 0)

        return qa(ticker_a, ticker_b) - qb(ticker_a, ticker_b)

    def t(self, ticker_a, ticker_b):
        return ticker_a.last - ticker_b.last

    def use(self, strategy):
        strategy.logger.info("OrderImbalance is loading...")

    def bizlogic(self, ohlcv, ticker, position, balance, execution, strategy, **other):



        pos = Dotdict(position)
        strategy.logger.debug("Execution:" + str(execution))
        # strategy.logger.debug("Position:" + str(pos))

        # strategy.logger.debug("Status: %s %s %s" % (self.followLogic.is_following,
        #                                       self.followLogic.last_orderid is not None,
        #                                       strategy.exchange.om.is_active(self.followLogic.last_orderid)))
        if self.followLogic.is_following \
                and self.followLogic.last_orderid is not None \
                and strategy.exchange.om.is_active(self.followLogic.last_orderid):
            self.followLogic.close_order(ticker)
        elif pos.openOrderBuyQty == 0 and pos.openOrderSellQty == 0:
            self.testLogic.create_orders(ticker)
        elif pos.openOrderBuyQty > pos.openOrderSellQty:
            leave_qty = pos.openOrderBuyQty - pos.openOrderSellQty
            self.testLogic.executed(ticker, 'sell', leave_qty)
        elif pos.openOrderSellQty > pos.openOrderBuyQty:
            leave_qty = pos.openOrderSellQty - pos.openOrderBuyQty
            self.testLogic.executed(ticker, 'buy', leave_qty)
        if self.testLogic.last_my_test_orders.ask != ticker.ask - SPREAD \
                and self.testLogic.last_my_test_orders.asksize != ticker.asksize \
                and not self.followLogic.is_following:
            self.testLogic.amend_orders(ticker, 'sell')
        if self.testLogic.last_my_test_orders.bid != ticker.bid + SPREAD \
                and self.testLogic.last_my_test_orders.bidsize != ticker.bidsize \
                and not self.followLogic.is_following:
            self.testLogic.amend_orders(ticker, 'buy')


if __name__ == "__main__":
    strategy = Strategy(TestAndTrendfollow)

    strategy.settings.interval = 10

    strategy.start()
