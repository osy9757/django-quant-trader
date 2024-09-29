from django.test import TestCase
from .services import UpbitDataProvider
from .models import UpbitData

class UpbitDataProviderTest(TestCase):
    def test_data_fetch_and_save(self):
        provider = UpbitDataProvider(currency="BTC", interval=60)
        data = provider.get_info()
        
        self.assertIsNotNone(data)
        self.assertTrue(UpbitData.objects.filter(market=data["market"]).exists())
