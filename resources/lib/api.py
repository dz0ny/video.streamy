# -*- coding: utf-8 -*-

import logging
from collections import namedtuple

import requests
import re
from urllib import unquote, urlencode, quote_plus
from resources.lib import cache as cachetool
from trakt import Trakt
from trakt.objects import Movie, Show
from xbmcgui import ListItem
from os import path
cache = cachetool.Cache()
logger = logging.getLogger(__name__)
    
class Streamy(object):
    root = None

    def __init__(self, root):
        self.root = root

    def url(self, sec):
        return path.join(
            self.root,
            sec[1:] if sec.startswith('/') else sec
        )

    def ping(self):
        try:
            req = requests.get(self.url('ping'))
            req.raise_for_status()
            return True
        except Exception as e:
            return False

    def torrents(self):
        req = requests.get(self.url('torrents'))
        req.raise_for_status()
        for t in req.json():
            yield t['name'], t['ih']
        
    def torrent(self, ih, magnet=None):
        if magnet:
            req = requests.get(self.url('torrents/add'), params={
                'magnet': magnet,
            })
        else:
            req = requests.get(self.url('torrents/' + ih))
        req.raise_for_status()
        data = req.json()
        if data.get('files'):
            for f in data['files']:
                name = '/'.join(f['Path'])
                yield name, self.url(f['data']), f['Length']
        else:
            name = data['name']
            url = '/torrents/{}/stream?file={}'.format(data['ih'], name)
            yield name, self.url(url), 0

class fetchapi(object):
    BASE_URL = "https://movies-v2.api-fetch.website"

    def __init__(self):
        self.r = requests.Session()
        self.r.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
            }
        )

    def get_movies(self, type_, limit, search):
        data = []
        for x in range(1, limit):
            url = '{}/movies/{}?sort={}'.format(self.BASE_URL, x, type_)
            if search:
                url += '&keywords={}'.format(search)
            res = cache.get(self, url)
            if not res:
                req = self.r.get(url)
                req.raise_for_status()
                res = req.json()
                cache.set(self, url, res, 48)
            data.extend(res)
        return data

    def get_shows(self, type_, limit, search):
        data = []
        for x in range(1, limit):
            url = '{}/shows/{}?sort={}'.format(self.BASE_URL, x, type_)
            if search:
                url += '&keywords={}'.format(search)
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
        for t in res:
            yield self.parse(t)

    def search(self, c):
        url = "&sort=seeders&limit=100&mode=search&search_string=" + c
        url = self.BASE_URL + "?token=" + self.token + url
        res = cache.get(self, url)
        if not res:
            req = self.r.get(url)
            req.raise_for_status()
            res = req.json()['torrent_results']
            cache.set(self, url, res)
        for t in res:
            yield self.parse(t)

    def parse(self, obj):
        return obj['title'], obj['download']

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
