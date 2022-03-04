from yatube.settings import CACHE_TIME


def cache_time(request):
    return {'cache_time': CACHE_TIME}
