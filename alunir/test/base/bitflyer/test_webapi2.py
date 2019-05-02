# -*- coding: utf-8 -*-
import time

from xross_common.XrossTestBase import XrossTestBase
from xross_common.SystemUtil import SystemUtil

from alunir.main.base.bitflyer.webapi2 import LightningAPI


class TestLightningAPI(XrossTestBase):
    def setUp(self):
        cfg = SystemUtil(skip=True)
        self.api = LightningAPI(cfg.get_env("BITFLYER_LIGHTNING_USERID"), cfg.get_env("BITFLYER_LIGHTNING_PASSWORD"))

    # TODO: Automatically input 2 Factor Code
    # def test_login(self):
    #     self.api.login()
    #
    #     self.assertTrue(self.api.logon)


if __name__ == '__main__':
    TestLightningAPI.do_test()
