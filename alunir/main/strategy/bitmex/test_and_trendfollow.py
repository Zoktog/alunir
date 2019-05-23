# -*- coding: utf-8 -*-
from alunir.main.base.bitmex.strategy import Strategy
from alunir.main.base.common.strategy import StrategyBase
from xross_common.Dotdict import Dotdict

SPREAD = 100
TEST_QUANTITY = 10
FOLLOW_QUANTITY = 1000


class FollowLogic:
    strategy = None

    def __init__(self, strategy):
        self.strategy = strategy
        self.is_following = False
        self.side = None
        self.qty = None
        self.last_orderid = None

    def follow(self, side, limit, qty, stop_loss):  # MEMO: order FOLLOW_QUONTITY as soon as executed test orders.
        self.strategy.logger.info("FOLLOWING MODE IS STARTED")
        self.is_following = True
        self.side = side
        self.qty = FOLLOW_QUANTITY + qty
        if side == 'buy':
            self.strategy.entry('FB', 'buy', self.qty, limit=limit, stop=stop_loss)
            self.last_orderid = 'FB'
        elif side == 'sell':
            self.strategy.entry('FS', 'sell', self.qty, limit=limit, stop=stop_loss)
            self.last_orderid = 'FS'
        else:
            raise ValueError("side should be 'buy' or 'sell'")

    def close_order(self, ticker):
        # if close condition:
        if self.side == 'sell':
            strategy.logger.debug("Amend Following Sell %s" % max(ticker.ask - SPREAD, ticker.bid))
            strategy.edit_order('FS', 'sell', self.qty, limit=max(ticker.ask - SPREAD, ticker.bid))
        elif self.side == 'buy':
            strategy.logger.debug("Amend Following Buy %s" % min(ticker.bid + SPREAD, ticker.ask))
            strategy.edit_order('FB', 'buy', self.qty, limit=min(ticker.bid + SPREAD, ticker.ask))
        else:
            pass


class TestLogic:
    strategy = None
    last_my_test_orders = Dotdict({"ask": None, "bid": None})

    def __init__(self, strategy, followLogic):
        self.strategy = strategy
        self.followLogic = followLogic

    # MEMO: create new both orders
    def create_orders(self, ticker):
        if self.followLogic.is_following:
            self.followLogic.last_orderid = None
            self.strategy.logger.info("FOLLOWING MODE IS STOPPED")
        self.followLogic.is_following = False
        _ask = ticker.ask - SPREAD
        _bid = ticker.bid + SPREAD
        strategy.logger.debug("New Buy %s and New Sell %s" % (_ask, _bid))
        strategy.entry('B', 'buy', TEST_QUANTITY, limit=_bid)
        strategy.entry('S', 'sell', TEST_QUANTITY, limit=_ask)
        self.last_my_test_orders.ask = _ask
        self.last_my_test_orders.bid = _bid
        self.last_my_test_orders.asksize = TEST_QUANTITY
        self.last_my_test_orders.bidsize = TEST_QUANTITY

    def amend_orders(self, ticker, side):
        if side == 'sell':
            if ticker.ask == self.last_my_test_orders.ask:
                amend_price = max(ticker.ask - SPREAD, ticker.bid)
            else:
                amend_price = max(ticker.asks[1][0] - SPREAD, ticker.bid)
            strategy.logger.debug("Amend Sell %s" % amend_price)
            strategy.edit_order('S', 'sell', TEST_QUANTITY, limit=amend_price)
            self.last_my_test_orders.ask = amend_price
            self.last_my_test_orders.asksize = TEST_QUANTITY
        elif side == 'buy':
            if ticker.bid == self.last_my_test_orders.bid:
                amend_price = min(ticker.bid + SPREAD, ticker.ask)
            else:
                amend_price = min(ticker.bids[1][0] + SPREAD, ticker.ask)
            strategy.logger.debug("Amend Buy %s" % amend_price)
            strategy.edit_order('B', 'buy', TEST_QUANTITY, limit=amend_price)
            self.last_my_test_orders.bid = amend_price
            self.last_my_test_orders.bidsize = TEST_QUANTITY
        else:
            pass

    def executed(self, ticker, executed_side, executed_qty):
        if executed_side == 'sell':
            strategy.logger.debug("Executed Sell %s then Others cancel and Decrease BuyVolume" % executed_qty)
            if executed_qty == TEST_QUANTITY:
                strategy.cancel('S')
            strategy.cancel('B')
            self.followLogic.follow('buy', ticker.ask, executed_qty, ticker.bid)
        elif executed_side == 'buy':
            strategy.logger.debug("Executed Buy %s then Others cancel and Decrease SellVolume" % executed_qty)
            strategy.cancel('S')
            if executed_qty == TEST_QUANTITY:
                strategy.cancel('B')
            self.followLogic.follow('sell', ticker.bid, executed_qty, ticker.ask)
        else:
            pass


class TestAndTrendfollow(StrategyBase):
    qty = None
    testLogic = None
    followLogic = None

    def use(self, strategy):
        strategy.logger.info("TestLogic and FollowLogic is loading...")
        self.followLogic = FollowLogic(strategy)
        self.testLogic = TestLogic(strategy, self.followLogic)

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
