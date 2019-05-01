# -*- coding: utf-8 -*-
from enum import Enum


class PriceType(Enum):
    MARKET = ('MARKET', None)
    LIMIT = ('LIMIT', 0.0)

    def __init__(self, name, price):
        self.name = name
        self.price = price
