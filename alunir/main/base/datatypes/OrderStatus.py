# -*- coding: utf-8 -*-
from enum import Enum


class OrderStatus(Enum):
    OPEN = ('OPEN', True, True, False)
    ACCEPTED = ('ACCEPTED', True, True, False)
    CANCEL = ('CANCEL', True, False, False)
    CANCELLED = ('CANCELLED', False, False, True)
    CLOSE = ('CLOSE', False, True)

    def __init__(self, name, living, cancelable, dead):
        self.name = name
        self.living = living
        self.cancelable = cancelable
        self.dead = dead
