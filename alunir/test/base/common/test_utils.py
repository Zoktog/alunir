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
        d = ReloadableJsondict('test/resources/test.json')

        self.assertEqual(0, d.mtime)
        self.assertFalse(d.reloaded)
        self.assertRegex(d.path, '.*/common')


if __name__ == '__main__':
    TestUtil.do_test()
