import logging
from collections import namedtuple

import requests
import re
from urllib import unquote, urlencode, quote_plus
from resources.lib import cache as cachetool
from trakt import Trakt
from trakt.objects import Movie, Show
from xbmcgui import ListItem

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

    def get_movies(self, type_, limit):
        data = []
        for x in range(1, limit):
            url = '{}/movies/{}?sort={}'.format(self.BASE_URL, x, type_)
            res = cache.get(self, url)
            if not res:
                req = self.r.get(url)
                req.raise_for_status()
                res = req.json()
                cache.set(self, url, res, 48)
            data.extend(res)
        return data

    def get_shows(self, type_, limit):
        data = []
        for x in range(1, limit):
            url = '{}/shows/{}?sort={}'.format(self.BASE_URL, x, type_)
            res = cache.get(self, url)
            if not res:
                req = self.r.get(url)
                req.raise_for_status()
                res = req.json()
                cache.set(self, url, res, 48)
            data.extend(res)
        return data

    def get_show(self, id):
        url = '{}/show/{}'.format(self.BASE_URL, id)
        res = cache.get(self, url)
        if not res:
            req = self.r.get(url)
            req.raise_for_status()
            res = req.json()
            cache.set(self, url, res, 48)
        return res

    def search(self, k):
        url = '{}/movies/1?sort=trending&keywords={}'.format(self.BASE_URL, k)
        res = cache.get(self, url)
        if not res:
            req = self.r.get(url)
            req.raise_for_status()
            res = req.json()
            cache.set(self, url, res, 48)
        return res


class torapi(object):
    BASE_URL = "https://torrentapi.org/pubapi_v2.php"
    token_ = None

    def __init__(self):
        self.r = requests.Session()

    @property
    def token(self):
        TOKEN_URL = self.BASE_URL + "?get_token=get_token"
        req = self.r.get(TOKEN_URL)
        req.raise_for_status()
        return req.json()["token"]


    def category(self, c):
        url = '&category=' + c + "&format=json_extended&sort=seeders&limit=100"
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

    def sanitize(self, obj):
        info = dict(
            title=obj['title'],
            q='',
            ratio='S:{}/L:{}'.format(obj['seeders'], obj['leechers']),
        )
        parts = re.split(r'[\W\-]+', obj['title'])
        quas = ['720p', '1080p', 'hdrip', 'webrip', 'dvrip', 'web-dl']

        for part in parts:
            if part.encode('ascii').lower() in quas:
                info['q'] = part

        if 'Movies' in obj['category']:
            info['type'] = 'movie'
            title = []
            for x in parts:
                epinfo = re.match(r"(\d{4})", x)
                if epinfo:
                    info['year'] = int(epinfo.group(1))
                    break
                else:
                    title.append(x)
            info['title'] = ' '.join(title) 
        if 'TV' in obj['category']:
            info['type'] = 'episode'
            title = []
            for x in parts:
                epinfo = re.match(r"S(\d+)E(\d+)", x)
                if epinfo:
                    info['season'] = int(epinfo.group(1))
                    info['episode'] = int(epinfo.group(2))
                    break
                else:
                    title.append(x)
            info['title'] = ' '.join(title)   

        info = namedtuple('rarbg', info.keys())(**info)
        li = ListItem(obj['title'])
        if getattr(info, 'type', None):
            if info.type == 'movie':
                title = '{0.year}: {0.title} {0.q} {0.ratio}'.format(info)
                trailer = quote_plus('{0.title} trailer'.format(info))
                li = ListItem(title)
                li.addContextMenuItems([
                    ('Trailer', 'Container.Update(plugin://plugin.video.youtube/kodion/search/query/?q={})'.format(trailer)),
                ])

            elif info.type == 'episode':
                if getattr(info, 'date', None):
                    title = '{0.title} {0.date} {0.q} {0.ratio}'.format(info)
                    trailer = quote_plus('{0.title} trailer'.format(info))
                    li = ListItem(title)
                    li.addContextMenuItems([
                        ('Trailer', 'Container.Update(plugin://plugin.video.youtube/kodion/search/query/?q={})'.format(trailer)),
                    ])
                else:
                    title = '{0.title} S{0.season:02d}E{0.episode:02d} {0.q} {0.ratio}'.format(info)
                    trailer = quote_plus('{0.title} trailer'.format(info))
                    li = ListItem(title)
                    li.addContextMenuItems([
                        ('Trailer', 'Container.Update(plugin://plugin.video.youtube/kodion/search/query/?q={})'.format(trailer)),
                    ])
        return li


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
