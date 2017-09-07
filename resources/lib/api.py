import requests

from resources.lib import cache as cachetool

cache = cachetool.Cache()


class fetchapi(object):
    BASE_URL = "https://movies-v2.api-fetch.website"

    def __init__(self):
        self.r = requests.Session()
        self.r.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
            }
        )

    def get_movies(self):
        data = []
        for x in range(1, 25):
            url = '{}/movies/{}?sort=trending'.format(self.BASE_URL, x)
            res = cache.get(self, url)
            if not res:
                req = self.r.get(url)
                req.raise_for_status()
                res = req.json()
                cache.set(self, url, res)
            data.extend(res)
        return data

    def get_shows(self):
        data = []
        for x in range(1, 25):
            url = '{}/shows/{}?sort=trending'.format(self.BASE_URL, x)
            res = cache.get(self, url)
            if not res:
                req = self.r.get(url)
                req.raise_for_status()
                res = req.json()
                cache.set(self, url, res)
            data.extend(res)
        return data

    def get_show(self, id):
        url = '{}/show/{}'.format(self.BASE_URL, id)
        res = cache.get(self, url)
        if not res:
            req = self.r.get(url)
            req.raise_for_status()
            res = req.json()
            cache.set(self, url, res)
        return res

    def search(self, k):
        url = '{}/movies/1?sort=trending&keywords={}'.format(self.BASE_URL, k)
        res = cache.get(self, url)
        if not res:
            req = self.r.get(url)
            req.raise_for_status()
            res = req.json()
            cache.set(self, url, res)
        return res


class torapi(object):
    BASE_URL = "https://torrentapi.org/pubapi_v2.php"
    token_ = None

    def __init__(self):
        self.r = requests.Session()
        self.r.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
            }
        )

    @property
    def token(self):
        self.token_ = cache.get(self, 'token')
        if not self.token_:
            TOKEN_URL = self.BASE_URL + "?get_token=get_token"
            req = self.r.get(TOKEN_URL)
            req.raise_for_status()
            self.token_ = req.json()["token"]
            cache.set(self, 'token', self.token_)
        return self.token_

    def category(self, c):
        url = "&sort=seeders&limit=100&category=" + c
        url = self.BASE_URL + "?token=" + self.token + url
        res = cache.get(self, url)
        if not res:
            req = self.r.get(url)
            req.raise_for_status()
            res = req.json()['torrent_results']
            cache.set(self, url, res)
        return res

    def search(self, c):
        url = "&sort=seeders&limit=100&mode=search&search_string=" + c
        url = self.BASE_URL + "?token=" + self.token + url
        res = cache.get(self, url)
        if not res:
            req = self.r.get(url)
            req.raise_for_status()
            res = req.json()['torrent_results']
            cache.set(self, url, res)
        return res
