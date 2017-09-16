import requests
import logging

from resources.lib import cache as cachetool
from trakt import Trakt
from trakt.objects import Movie, Show

cache = cachetool.Cache()
logger = logging.getLogger(__name__)

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


class traktAPI(object):
    __client_id = "d4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868"
    __client_secret = "b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0"

    def __init__(self, force=False):
        logger.debug("Initializing.")

        proxyURL = checkAndConfigureProxy()
        if proxyURL:
            Trakt.http.proxies = {
                'http': proxyURL,
                'https': proxyURL
            }

        # Configure
        Trakt.configuration.defaults.client(
            id=self.__client_id,
            secret=self.__client_secret
        )

    def getMovieSummary(self, movieId):
        with Trakt.configuration.http(retry=True):
            return Trakt['movies'].get(movieId)

    def getShowSummary(self, showId):
        with Trakt.configuration.http(retry=True):
            return Trakt['shows'].get(showId)

    def getShowWithAllEpisodesList(self, showId):
        with Trakt.configuration.http(retry=True, timeout=90):
            return Trakt['shows'].seasons(showId, extended='episodes')

    def getEpisodeSummary(self, showId, season, episode):
        with Trakt.configuration.http(retry=True):
            return Trakt['shows'].episode(showId, season, episode)

    def getIdLookup(self, id, id_type):
        with Trakt.configuration.http(retry=True):
            result = Trakt['search'].lookup(id, id_type)
            if result and not isinstance(result, list):
                result = [result]
            return result

    def getTextQuery(self, query, type, year):
        with Trakt.configuration.http(retry=True, timeout=90):
            result = Trakt['search'].query(query, type, year)
            if result and not isinstance(result, list):
                result = [result]
            return result
