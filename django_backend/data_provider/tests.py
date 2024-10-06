from django.test import TestCase
from unittest.mock import patch, Mock, MagicMock
from .services import UpbitDataProvider
from .models import UpbitData

class UpbitDataProviderTest(TestCase):
    def setUp(self):
        self.provider = UpbitDataProvider(currency="BTC", interval=60)

    def test_data_fetch_and_save(self):
        data = self.provider.get_info()

        self.assertIsNotNone(data)
        self.assertTrue(UpbitData.objects.filter(market=data["market"]).exists())

    @patch('requests.get')
    def test_fetch_historical_data(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "market": "BTC-KRW",
            "candles": [
                {"timestamp": "2023-10-01T00:00:00+09:00", 
                 "opening_price": 1000000, 
                 "high_price": 1050000, 
                 "low_price": 950000, 
                 "closing_price": 1020000, 
                 "candle_acc_trade_volume": 100000000, 
                 "candle_acc_trade_price": 1000000000000000}
            ]
        }

        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        self.provider.fetch_historical_data(start_date="2024-10-05T00:00:00+09:00")

        self.assertTrue(UpbitData.objects.filter(market=self.provider.query_string).exists())
