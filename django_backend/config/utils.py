def generate_redis_key(provider_name, market, timeframe='1m'):
    """
    Redis 키를 생성하는 함수
    """

    return f"{provider_name}:{market}:{timeframe}"