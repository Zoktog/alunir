# -*- coding: utf-8 -*-
import unittest


class TestBase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # noinspection PyMethodParameters
    def do_test():
        unittest.main()
