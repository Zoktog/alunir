# -*- coding: utf-8 -*-
from alunir.main.base.bitmex.strategy import Strategy
from alunir.main.base.common.strategy import StrategyBase
from xross_common.Dotdict import Dotdict

QUANTITY = 200


class SampleStrategy(StrategyBase):
    spread = 200
    qty = None
    last_my_order = Dotdict({"ask": None, "bid": None})
    last_ticker = Dotdict({"ask": None, "bid": None})

    def use(self, strategy):
        pass

    def bizlogic(self, ohlcv, ticker, position, balance, execution, strategy, **other):
        pos = Dotdict(position)
        strategy.logger.debug("Execution:" + str(execution))
        # strategy.logger.debug("Position:" + str(pos))

        if pos.openOrderBuyQty == 0 and pos.openOrderSellQty == 0:
            strategy.logger.debug("New Buy %s and New Sell %s" % (ticker.bid + self.spread, ticker.ask - self.spread))
            strategy.entry('B', 'buy', QUANTITY, limit=ticker.bid + self.spread)
            strategy.entry('S', 'sell', QUANTITY, limit=ticker.ask - self.spread)
            self.last_my_order.ask = ticker.ask - self.spread
            self.last_my_order.bid = ticker.bid + self.spread
            self.qty = QUANTITY
        elif pos.openOrderBuyQty > pos.openOrderSellQty > 0:  # MEMO: hedge order should be shadow
            leave_qty = pos.openOrderBuyQty - pos.openOrderSellQty
            strategy.logger.debug("Partially Executed Sell %s then Others cancel and Decrease BuyVolume" % leave_qty)
            strategy.cancel('S')
            strategy.edit_order('B', 'buy', leave_qty)
            self.qty = leave_qty
        elif pos.openOrderSellQty > pos.openOrderBuyQty > 0:  # MEMO: hedge order should be shadow
            leave_qty = pos.openOrderSellQty - pos.openOrderBuyQty
            strategy.logger.debug("Partially Executed Buy %s then Others cancel and Decrease SellVolume" % leave_qty)
            strategy.cancel('B')
            strategy.edit_order('S', 'sell', leave_qty)
            self.qty = leave_qty
        elif pos.openOrderBuyQty > pos.openOrderSellQty == 0:  # MEMO: hedge order should be shadow
            strategy.logger.debug("Fully Executed Sell then Amend Buy %s" % min(self.last_my_order.bid, ticker.ask))
            # strategy.logger.info(self.last_ticker.bids)
            if self.last_ticker.bid != ticker.bid:
                strategy.edit_order('B', 'buy', self.qty, limit=min(ticker.bid + self.spread, ticker.ask))
                self.last_my_order.bid = min(ticker.bid + self.spread, ticker.ask)
            # elif self.last_ticker.bids[1][0] != ticker.bids[1][0]:  # MEMO: except self order
            #     strategy.edit_order('B', 'buy', self.qty, limit=min(ticker.bids[1][0] + self.spread, self.last_my_order.ask, ticker.ask))
            #     self.last_my_order.bid = min(ticker.bids[1][0] + self.spread, ticker.ask)
            else:
                pass
        elif pos.openOrderSellQty > pos.openOrderBuyQty == 0:  # MEMO: hedge order should be shadow
            strategy.logger.debug("Fully Executed Buy then Amend Sell %s" % max(self.last_my_order.ask, ticker.bid))
            # strategy.logger.info(self.last_ticker.asks)
            if self.last_ticker.ask != ticker.ask:
                strategy.edit_order('S', 'sell', self.qty, limit=max(ticker.ask - self.spread, ticker.bid))
                self.last_my_order.ask = max(ticker.ask - self.spread, ticker.bid)
            # elif self.last_ticker.asks[1][0] != ticker.bids[1][0]:
            #     strategy.edit_order('S', 'sell', self.qty, limit=max(ticker.asks[1][0] - self.spread, self.last_my_order.bid, ticker.bid))
            #     self.last_my_order.bid = min(ticker.asks[1][0] - self.spread, ticker.bid)
            else:
                pass
        elif self.last_my_order.ask > ticker.ask:
            strategy.logger.debug("Amend Sell %s" % max(ticker.ask - self.spread, ticker.bid, self.last_my_order.ask))
            strategy.edit_order('S', 'sell', self.qty, limit=max(ticker.ask - self.spread, ticker.bid, self.last_my_order.ask))
            self.last_my_order.ask = max(ticker.ask - self.spread, ticker.bid, self.last_my_order.ask)
        elif self.last_my_order.bid < ticker.bid:
            strategy.logger.debug("Amend Buy %s" % min(ticker.bid + self.spread, ticker.ask, self.last_my_order.bid))
            strategy.edit_order('B', 'buy', self.qty, limit=min(ticker.bid + self.spread, ticker.ask, self.last_my_order.bid))
            self.last_my_order.bid = min(ticker.bid + self.spread, ticker.ask, self.last_my_order.bid)
        else:
            pass
        self.last_ticker = ticker


if __name__ == "__main__":
    strategy = Strategy(SampleStrategy)

    strategy.settings.interval = 5

    strategy.start()
