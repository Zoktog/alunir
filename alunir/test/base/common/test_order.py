# -*- coding: utf-8 -*-
from xross_common.XrossTestBase import XrossTestBase

from alunir.main.base.common.order import OrderManager, OrderNotFoundException


class TestOrderManager(XrossTestBase):
    def setUp(self):
        self.om = OrderManager()
        self.om.printall()

    def tearDown(self):
        self.om.clear_for_test()

    def test_OrderNotFoundException(self):
        try:
            self.om.get_order('test1')
            self.fail()
        except OrderNotFoundException as e:
            self.assertEqual("MyOrderID:test1 is not found. MyOrders:[]", str(e))

    def test_add_order(self):
        o = OrderManager.INVALID_ORDER.copy()
        o['id'] = 'id_returned_from_exchange'
        o['myid'] = 'test1'
        o['status'] = 'open'
        o['type'] = 'limit'
        o['price'] = 1
        o['side'] = 'L'
        self.assertDictEqual(
            {'No': 1,
             'amount': 0,
             'average_price': 0,
             'accepted_at': '1989-10-28T0:00:00.000',
             'fee': 0,
             'filled': 0,
             'id': 'id_returned_from_exchange',
             'myid': 'test1',
             'price': 1,
             'remaining': 0,
             'side': 'L',
             'status': 'open',
             'symbol': 'FX_BTC_JPY',
             'type': 'limit'}
            , self.om.add_order(o)
        )

        self.assertDictEqual(
            {'No': 1,
             'amount': 0,
             'average_price': 0,
             'accepted_at': '1989-10-28T0:00:00.000',
             'fee': 0,
             'filled': 0,
             'id': 'id_returned_from_exchange',
             'myid': 'test1',
             'price': 1,
             'remaining': 0,
             'side': 'L',
             'status': 'open',
             'symbol': 'FX_BTC_JPY',
             'type': 'limit'}
            , self.om.get_order('test1')
        )
        self.om.printall()

    def test_add_order2(self):
        self.test_add_order()

        o = OrderManager.INVALID_ORDER.copy()
        o['id'] = 'id_returned_from_exchange'
        o['myid'] = 'test2'
        o['status'] = 'open'
        o['side'] = 'S'
        self.om.add_order(o)

        self.assertDictEqual(
            {'No': 2,
             'amount': 0,
             'average_price': 0,
             'accepted_at': '1989-10-28T0:00:00.000',
             'fee': 0,
             'filled': 0,
             'id': 'id_returned_from_exchange',
             'myid': 'test2',
             'price': 0,
             'remaining': 0,
             'side': 'S',
             'status': 'open',
             'symbol': 'FX_BTC_JPY',
             'type': 'market'}
            , self.om.get_order('test2')
        )
        self.om.printall()

    def test_update_order1(self):
        self.test_add_order2()

        o = self.om.get_order('test1')
        o['filled'] = '1'
        o['remaining'] = '2'
        self.om.update_order(o)
        self.assertDictEqual(
            {'No': 1,
             'amount': 0,
             'average_price': 0,
             'accepted_at': '1989-10-28T0:00:00.000',
             'fee': 0,
             'filled': '1',
             'id': 'id_returned_from_exchange',
             'myid': 'test1',
             'price': 1,
             'remaining': '2',
             'side': 'L',
             'status': 'open',
             'symbol': 'FX_BTC_JPY',
             'type': 'limit'}
            , self.om.get_order('test1')
        )
        self.om.printall()

    def test_update_order2(self):
        self.test_update_order1()

        o = self.om.get_order('test2')
        o['filled'] = '1'
        o['remaining'] = '2'
        self.om.update_order(o)
        self.assertDictEqual(
            {'No': 2,
             'amount': 0,
             'average_price': 0,
             'accepted_at': '1989-10-28T0:00:00.000',
             'fee': 0,
             'filled': '1',
             'id': 'id_returned_from_exchange',
             'myid': 'test2',
             'price': 0,
             'remaining': '2',
             'side': 'S',
             'status': 'open',
             'symbol': 'FX_BTC_JPY',
             'type': 'market'}
            , self.om.get_order('test2')
        )
        self.om.printall()

    def test_cancel_order1(self):
        self.test_update_order2()

        self.om.cancel_order('test1')

        self.assertDictEqual(
            {'No': 1,
             'amount': 0,
             'average_price': 0,
             'accepted_at': '1989-10-28T0:00:00.000',
             'fee': 0,
             'filled': '1',
             'id': 'id_returned_from_exchange',
             'myid': 'test1',
             'price': 1,
             'remaining': '2',
             'side': 'L',
             'status': 'cancel',
             'symbol': 'FX_BTC_JPY',
             'type': 'limit'}
            , self.om.get_order('test1')
        )
        self.om.printall()

    def test_cancel_order2(self):
        self.test_cancel_order1()

        self.om.cancel_order('test2')  # type 'market' was not cancelled.

        self.assertDictEqual(
            {'No': 2,
             'amount': 0,
             'average_price': 0,
             'accepted_at': '1989-10-28T0:00:00.000',
             'fee': 0,
             'filled': '1',
             'id': 'id_returned_from_exchange',
             'myid': 'test2',
             'price': 0,
             'remaining': '2',
             'side': 'S',
             'status': 'open',
             'symbol': 'FX_BTC_JPY',
             'type': 'market'}
            , self.om.get_order('test2')
        )


if __name__ == '__main__':
    TestOrderManager.do_test()
