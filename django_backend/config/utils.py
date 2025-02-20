# django_backend/config/utils.py
def generate_redis_key(provider_name, market, timeframe='1m'):
    """
    Redis 키를 생성하는 함수.
    
    TODO: 이 함수는 현재 provider_name, market, timeframe을 조합하여 키를 생성합니다.
    추후 필요할 경우 새로운 인자를 추가하여 확장 가능하게 수정해야 합니다.
    """
    # FIXME: 현재 이 함수는 provider_name이 하드코딩되어 있는 경우를 가정합니다.
    # provider_name이 다를 경우 충돌할 수 있으니, 나중에 예외 처리를 추가해야 합니다.
    return f"{provider_name}:{market}:{timeframe}"

# NOTE: 현재는 'upbit'에 대해서만 이 함수를 사용하고 있지만, 
# 향후 다른 데이터 제공자(ex: 'binance')를 포함하도록 로직을 확장해야 함.
