import simplecache
import datetime
import pickle


class Cache(simplecache.SimpleCache):

    def get(self, cls, key, default=None):
        key = '{}.{}'.format(cls.__class__, key)
        res = super(Cache, self).get(key)
        return pickle.loads(res) if res else default

    def set(self, cls, key, val, exp=4):
        key = '{}.{}'.format(cls.__class__, key)
        val = pickle.dumps(val)
        exp = datetime.timedelta(hours=exp)
        res = super(Cache, self).set(key, val, expiration=exp)
        return res
