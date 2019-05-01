# -*- coding: utf-8 -*-
from datetime import datetime
from xross_common.Dotdict import Dotdict
from alunir.main.base.datatypes.PriceType import PriceType
from alunir.main.base.datatypes.BuySell import BuySell

INVALID_ORDER_ID = '__INVALID_ORDER__'


class WorkingOrder(Dotdict):
    No = 0
    myid = INVALID_ORDER_ID
    id = INVALID_ORDER_ID
    accepted_at = '1989-10-28T0:00:00.000'
    status = 'closed'
    symbol = 'FX_BTC_JPY'
    price_type = 'market'
    side = 'none'
    price = 0
    average_price = 0
    amount = 0
    filled = 0
    remaining = 0
    fee = 0

    def __init__(self, myid, id, symbol, buysell: BuySell, price_type: PriceType, qty, accepted_at=None):
        super().__init__()
        self.myid = myid
        self.accepted_at = accepted_at if accepted_at else datetime.utcnow()
        self.id = id
        self.symbol = symbol
        self.price_type = price_type.name
        self.side = buysell.char
        self.price = price_type.price
        self.amout = qty
