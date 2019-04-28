# -*- coding: utf-8 -*-
from xross_common.XrossTestBase import XrossTestBase

from alunir.main.base.common.order import OrderManager


class TestOrderManager(XrossTestBase):
    def setUp(self):
        self.om = OrderManager()
        self.om.printall()

    def test_add_order(self):
        o = OrderManager.INVALID_ORDER.copy()
        o['id'] = 'test1'
        o['status'] = 'open'
        o['side'] = 'L'
        self.assertDictEqual(
            {'No': 1,
             'amount': 0,
             'average_price': 0,
             'datetime': '2018-9-1T0:00:00.000',
             'fee': 0,
             'filled': 0,
             'id': 'test1',
             'myid': '__INVALID_ORDER__',
             'price': 0,
             'remaining': 0,
             'side': 'L',
             'status': 'open',
             'symbol': 'FX_BTC_JPY',
             'type': 'market'}
            , self.om.add_order(o)
        )

        self.assertDictEqual(
            {'No': 0,
             'amount': 0,
             'average_price': 0,
             'datetime': '2018-9-1T0:00:00.000',
             'fee': 0,
             'filled': 0,
             'id': '__INVALID_ORDER__',
             'myid': 'test1',
             'price': 0,
             'remaining': 0,
             'side': 'none',
             'status': 'closed',
             'symbol': 'FX_BTC_JPY',
             'type': 'market'}
            , self.om.get_order('test1')
        )
        self.om.printall()

    def test_add_order2(self):
        self.test_add_order()

        o = OrderManager.INVALID_ORDER.copy()
        o['id'] = 'test2'
        o['status'] = 'open'
        o['side'] = 'S'
        self.om.add_order(o)

        self.assertDictEqual(
            {'No': 0,
             'amount': 0,
             'average_price': 0,
             'datetime': '2018-9-1T0:00:00.000',
             'fee': 0,
             'filled': 0,
             'id': '__INVALID_ORDER__',
             'myid': 'test2',
             'price': 0,
             'remaining': 0,
             'side': 'none',
             'status': 'closed',
             'symbol': 'FX_BTC_JPY',
             'type': 'market'}
            , self.om.get_order('test2')
        )
        self.om.printall()

    def test_update_order1(self):
        self.test_add_order2()

        o = self.om.get_order('L')
        o['filled'] = '1'
        o['remaining'] = '2'
        self.om.update_order(o)
        print('update', self.om.get_order('L'))
        self.om.printall()

    def test_update_order2(self):
        self.test_update_order1()

        o = self.om.get_order('S')
        o['filled'] = '1'
        o['remaining'] = '2'
        self.om.update_order(o)
        print('update', self.om.get_order('S'))
        self.om.printall()

    def test_cancel_order1(self):
        self.test_update_order2()

        print(self.om.cancel_order('L'))
        print('cancel', self.om.get_order('L'))
        self.om.printall()

    def test_cancel_order2(self):
        self.test_cancel_order1()

        print(self.om.cancel_order('S'))
        print('cancel', self.om.get_order('L'))
        self.om.printall()

        print(self.om.get_orders())


if __name__ == '__main__':
    TestOrderManager.do_test()
