# -*- coding: utf-8 -*-
from enum import Enum


class BuySell(Enum):
    BUY = ('BUY', 'B', False, False)
    MARGIN_BUY = ('MARGIN_BUY', 'B', True, False)
    SELL = ('SELL', 'S', False, False)
    SHORT_SELL = ('SHORT_SELL', 'S', True, False)
    SHORT_SELL_EXEMPT = ('SHORT_SELL_EXEMPT', 'S', True, True)

    def __init__(self, name, char, margin, exempt):
        self.name = name
        self.char = char
        self.margin = margin
        self.exempt = exempt
