# -*- coding: utf-8 -*-

import logging
from os import path
from urllib import unquote, urlencode
from urlparse import parse_qs, urlparse
from xml.etree import ElementTree

import requests

import routing
import xbmc
import xbmcaddon
from resources.lib import kodilogging, kodiutils
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory

try:
    import StorageServer
except:
    import storageserverdummy as StorageServer


ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))
kodilogging.config()
plugin = routing.Plugin()
cache = StorageServer.StorageServer(ADDON.getAddonInfo('id'), 4)


class fetchapi(object):
    BASE_URL = "https://movies-v2.api-fetch.website"

    def __init__(self):
        self.r = requests.Session()
        self.r.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
            }
        )

    def get_listing(self, cat):
        data = cache.get('ppc_{}'.format(cat))
        if 1:
            req = self.r.get(self.BASE_URL + '/{}'.format(cat))
            raise Exception(req.url)
            req.raise_for_status()
            movies = []
            
            for x in req.json():
                req = self.r.get(self.BASE_URL + x)
                req.raise_for_status()
                movies.extend(req.json())
            cache.set('ppc_{}'.format(cat), data)
        return data


class torapi(object):
    BASE_URL = "https://torrentapi.org/pubapi_v2.php"
    token_ = None

    @property
    def token(self):
        if not self.token_:
            TOKEN_URL = self.BASE_URL + "?get_token=get_token"
            request = requests.get(TOKEN_URL)
            self.token_ = request.json()["token"]
        return self.token_

    def category(self, c):
        url = "&min_seeders=5&min_leechers=5&sort=seeders&limit=100&category=" + c
        req = requests.get(self.BASE_URL + "?token=" + self.token + url)
        req.raise_for_status()
        return req.json()

    def search(self, c):
        url = "&sort=seeders&limit=100&mode=search&search_string=" + c
        req = requests.get(self.BASE_URL + "?token=" + self.token + url)
        req.raise_for_status()
        return req.json()


def str_url(sec):
    p = path.join(kodiutils.get_setting('server'), sec)
    return p

def ping():
    try:
        req = requests.get(str_url('ping'))
        req.raise_for_status()
        return True
    except Exception as e:
        kodiutils.notification("Cannot connect to server", str(e))
        return False

def directory(url, title, arg=None):
    addDirectoryItem(plugin.handle, plugin.url_for(url, arg) if arg else plugin.url_for(url), ListItem(title), True)

@plugin.route('/')
def index():
    if not ping():
        kodiutils.show_settings()
        return
    directory(show_torrents, 'Torrents')
    directory(show_videos, 'Videos')
    directory(show_shows_all, 'ShowRSS')
    directory(rarbg_all, 'RarBG')
    directory(popcorn_all, 'PopcornTime')
    endOfDirectory(plugin.handle)
    

@plugin.route('/popcorn_all')
def popcorn_all():
    directory(pocorn_cat, 'Movies', 'movies')
    directory(pocorn_cat, 'TV', 'shows')
    directory(pocorn_cat, 'Anime', 'animes')
    endOfDirectory(plugin.handle)
    

@plugin.route('/rarbg_all')
def rarbg_all():
    directory(rarbgc, 'Movies', '17;44;45;50;')
    directory(rarbgc, 'TV', '18;41;49;')
    directory(rarbgc, 'Music', '23;24;25;26;')
    directory(rarbgc, 'XXX', '4;')
    directory(rarbg_search, 'Search')
    endOfDirectory(plugin.handle)

@plugin.route('/shows_public')
def show_shows_all():
    try:
        req = requests.get('https://showrss.info/other/all.rss')
        req.raise_for_status()
        tree = ElementTree.fromstring(req.content)
        for t in tree.iter('item'):
            title = t.find('title').text
            ih = t.find('link').text
            addDirectoryItem(plugin.handle, plugin.url_for(show_torrent, ih='add', magnet=ih), ListItem(title), True)
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("Cannot connect to server", str(e))
        return
    

@plugin.route('/torrents')
def show_torrents():
    try:
        req = requests.get(str_url('torrents'))
        req.raise_for_status()
        for t in req.json():
            addDirectoryItem(plugin.handle, plugin.url_for(show_torrent, t['ih']), ListItem(t['name']), True)
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("Cannot connect to server", str(e))
        return


@plugin.route('/torrent/<ih>')
def show_torrent(ih=None):
    try:
        if 'magnet' in plugin.args:
            req = requests.get(str_url('torrent/add'), params={
                'magnet': unquote(plugin.args['magnet'][0]),
            })
        else:
            req = requests.get(str_url('torrent/{}'.format(ih)))
        req.raise_for_status()
        for f in req.json()['files']:
            addDirectoryItem(plugin.handle, "{}{}".format(kodiutils.get_setting('server'), f['data']), ListItem('/'.join(f['Path'])))
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification('Request', str(e))
        return

@plugin.route('/rarbg/<c>')
def rarbgc(c):
    try:
        t = torapi()
        for f in t.category(c)['torrent_results']:
            addDirectoryItem(plugin.handle, plugin.url_for(show_torrent, ih='add', magnet=f['download']), ListItem(f['filename']), True)
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("rarbg", str(e))
        return


@plugin.route('/pocorn_cat/<c>')
def pocorn_cat(c):
    try:
        t = fetchapi()
        for f in t.get_listing(c):
            li = xbmcgui.ListItem(label=f['title'])
            li.setArt({'poster': f['images']['poster'], 'fanart': f['images']['fanart']})
            li.setInfo(
                year=f['year'],
                plot=f['synopsis'],
                mediatype='movie',
                code=f['imdb_id'],
            )
            mag = f['torrents']['en']['1080p']['url']
            addDirectoryItem(plugin.handle, plugin.url_for(show_torrent, ih='add', magnet=mag), li, True)
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("Cannot connect to server", str(e))
        return



@plugin.route('/videos')
def show_videos():
    try:
        req = requests.get(str_url('torrents'))
        req.raise_for_status()
        for t in req.json():
            addDirectoryItem(plugin.handle, "{}{}".format(kodiutils.get_setting('server'), t['urls']['play']), ListItem(t['name']))
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("Cannot connect to server", str(e))
        return


@plugin.route('/search_rarbg')
def rarbg_search():
    keyboard = xbmc.Keyboard('', 'Search')
    keyboard.doModal()
    if keyboard.isConfirmed():
        keyboardinput = keyboard.getText()
        if keyboardinput:
            try:
                t = torapi()
                for f in t.search(keyboardinput)['torrent_results']:
                    addDirectoryItem(plugin.handle, plugin.url_for(show_torrent, ih='add', magnet=f['download']), ListItem(f['filename']), True)
                endOfDirectory(plugin.handle)
            except Exception as e:
                kodiutils.notification("rarbg", str(e))
                return


def run():
    plugin.run()
