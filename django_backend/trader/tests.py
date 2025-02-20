# django_backend/trader/tests.py
from django.test import TestCase
from trader.services import UpbitTrader


class UpbitTraderTestCase(TestCase):

    def setUp(self):

        self.trader = UpbitTrader()

    def test_get_account_info(self):

        account_info = self.trader.get_account_info()

        self.assertIsNotNone(account_info)
        self.assertIsInstance(account_info, list)

        if account_info:
            self.assertIn("currency", account_info[0])
            self.assertIn("balance", account_info[0])
            self.assertIn("locked", account_info[0])

    def test_send_and_cancel_order(self):

        def test_send_order(self):
            pass

        def test_cancel_order(self):
            pass
            
