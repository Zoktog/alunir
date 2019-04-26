# -*- coding: utf-8 -*-
from xross_common.XrossTestBase import XrossTestBase

from alunir.main.base.common.utils import Dotdict, ReloadableJsondict


class TestUtil(XrossTestBase):
    def test_dotdict(self):
        d = Dotdict({"a": 1, 'b': 4})

        self.assertEqual({'a': 1, 'b': 4}, d)
        self.assertEqual(1, d.a)
        self.assertEqual(4, d.b)

    def test_reloadablejsondict(self):
        d = ReloadableJsondict('/alunir/test/resources/test.json')

        self.assertTrue(d.mtime > 0)
        self.assertTrue(d.reloaded)
        self.assertRegex(d.path, '.*/alunir/test/resources/test.json')


if __name__ == '__main__':
    TestUtil.do_test()
