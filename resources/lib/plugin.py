# -*- coding: utf-8 -*-

import logging
from os import path
from urllib import unquote, urlencode, quote_plus
from urlparse import parse_qs, urlparse
from xml.etree import ElementTree
import requests

import routing
import xbmc
import xbmcaddon
from resources.lib import kodilogging, kodiutils
from resources.lib.api import fetchapi, torapi
from xbmcgui import ListItem
from xbmcplugin import (SORT_METHOD_DATE, SORT_METHOD_GENRE,
                        SORT_METHOD_UNSORTED, addDirectoryItem, addSortMethod,
                        endOfDirectory, setContent)

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))
kodilogging.config()
plugin = routing.Plugin()


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


def directory(url, title, *args):
    url = plugin.url_for(url, *args)
    addDirectoryItem(
        plugin.handle,
        url,
        ListItem(title),
        True,
    )


@plugin.route('/')
def index():
    if not ping():
        kodiutils.show_settings()
        return
    directory(show_torrents, 'Torrents')
    directory(show_shows_all, 'ShowRSS')
    directory(rarbg_all, 'RarBG')
    directory(popcorn_all, 'PopcornTime')
    endOfDirectory(plugin.handle)


@plugin.route('/popcorn_all')
def popcorn_all():
    directory(pocorn_movies, 'Movies', 'year', 50)
    directory(pocorn_movies, 'Movies - New', 'last added', 5)
    directory(pocorn_movies, 'Movies - Trending', 'trending', 5)
    directory(pocorn_movies, 'Movies - Rating', 'rating', 5)
    directory(popcorn_shows, 'TV', 'year', 50)
    directory(popcorn_shows, 'TV - New', 'last added', 5)
    directory(popcorn_shows, 'TV - Trending', 'trending', 5)
    directory(popcorn_shows, 'TV - Rating', 'rating', 5)
    endOfDirectory(plugin.handle)


@plugin.route('/rarbg_all')
def rarbg_all():
    directory(rarbgc, 'Movies', 'movies')
    directory(rarbgc, 'TV', 'tv')
    directory(rarbgc, 'Music', '23;24;25;26')
    directory(rarbgc, 'XXX', '4')
    directory(rarbg_search, 'Search')
    endOfDirectory(plugin.handle)


@plugin.route('/shows_public')
def show_shows_all():
    try:
        ss_id = kodiutils.get_setting('showrss_id')
        if ss_id != '':
            url = 'http://showrss.info/user/{}.rss?magnets=true&namespaces=true&name=clean&quality=null&re=null'.format(
                ss_id)
        else:
            url = 'https://showrss.info/other/all.rss'
        req = requests.get(url)
        req.raise_for_status()
        tree = ElementTree.fromstring(req.content)
        for t in tree.iter('item'):
            title = t.find('title').text
            ih = t.find('link').text
            addDirectoryItem(plugin.handle, plugin.url_for(
                show_torrent, ih='add', magnet=ih), ListItem(title), True)
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
            addDirectoryItem(plugin.handle, plugin.url_for(
                show_torrent, t['ih']), ListItem(t['name']), True)
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("Cannot connect to server", str(e))
        return


@plugin.route('/torrent/<ih>')
def show_torrent(ih=None):

    if 'magnet' in plugin.args:
        req = requests.get(str_url('torrents/add'), params={
            'magnet': unquote(plugin.args['magnet'][0]),
        })
    else:
        req = requests.get(str_url('torrents/{}'.format(ih)))
    req.raise_for_status()
    data = req.json()
    url = kodiutils.get_setting('server')
    if data['files']:
        for f in data['files']:
            addDirectoryItem(plugin.handle, "{}{}".format(
                url, f['data']), ListItem('/'.join(f['Path'])))
    else:
        addDirectoryItem(plugin.handle, "{}/torrents/{}/stream?file={}".format(
            url, data['ih'], data['name']), ListItem(data['name']))
    endOfDirectory(plugin.handle)


@plugin.route('/rarbg/<c>')
def rarbgc(c):
    try:
        t = torapi()
        for f in t.category(c):
            li = t.sanitize(f)
            addDirectoryItem(
                plugin.handle,
                plugin.url_for(show_torrent, ih='add', magnet=f['download']),
                li, True)

        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("rarbg", str(e))
        return


@plugin.route('/popcorn_shows/<c>/<l>')
def popcorn_shows(c, l):
    setContent(plugin.handle, 'tvshows')
    try:
        t = fetchapi()
        for f in t.get_shows(c, int(l)):
            li = ListItem(label=f['title'])
            try:
                li.setArt({
                    'poster': f['images']['poster'],
                    'fanart': f['images']['fanart']
                })
            except Exception:
                pass
            addDirectoryItem(
                plugin.handle,
                plugin.url_for(popcorn_show, f['imdb_id']),
                li,
                True
            )
        endOfDirectory(plugin.handle)
    except Exception as e:
        kodiutils.notification("popcorn", str(e))
        return


@plugin.route('/popcorn_show/<id>')
def popcorn_show(id):
    t = fetchapi()
    show = t.get_show(id)
    setContent(plugin.handle, 'episodes')
    episodes = sorted(show['episodes'], key=lambda f: (
        10000 * int(f['season'])) + int(f['episode']))
    for f in episodes:
        try:
            li = ListItem(label='{} S{:02d}E{:02d}: {}'.format(
                show['title'], int(f['season']), int(f['episode']), f['title']
            ))

            li.setInfo(
                'video',
                dict(
                    plot=f['overview'],
                    plotoutline=f['overview'],
                )
            )
            for k, v in f['torrents'].iteritems():
                mag = v['url']
                break

            addDirectoryItem(plugin.handle, plugin.url_for(
                show_torrent, ih='add', magnet=mag), li, True)
        except Exception:
            pass
    endOfDirectory(plugin.handle)


def to_yt(url):
    if url and 'youtube' not in url:
        return None
    try:
        url_data = urlparse(url)
        query = parse_qs(url_data.query)
        url = 'plugin://plugin.video.youtube/play/?video_id=' + query["v"][0]
        return url
    except Exception:
        return None


@plugin.route('/pocorn_movies/<c>/<l>')
def pocorn_movies(c, l):
    t = fetchapi()
    setContent(plugin.handle, 'movies')
    for f in t.get_movies(c, int(l)):
        li = ListItem(label=f['title'])
        try:
            li.setArt({
                'poster': f['images']['poster'],
                'fanart': f['images']['fanart']
            })
        except Exception:
            pass
        trailer = to_yt(f['trailer'])
        li.setInfo(
            'video',
            dict(
                plot=f['synopsis'],
                plotoutline=f['synopsis'],
                code=f['imdb_id'],
                genre='/'.join(f['genres']),
                imdbnumber=f['imdb_id'],
                year=f['year'],
                duration=int(f['runtime']) * 60,
                trailer=trailer,
            )
        )
        try:
            if f['trailer']:
                li.addContextMenuItems([
                    ('Trailer', 'PlayMedia({})'.format(trailer.encode('ascii'))),
                ])
        except Exception:
            pass
        torrents = f['torrents']['en']

        try:
            mag = torrents['720p']['url']
            mag = torrents['1080p']['url']
        except Exception:
            for k, v in torrents.iteritems():
                mag = v['url']
                break

        addDirectoryItem(plugin.handle, plugin.url_for(
            show_torrent, ih='add', magnet=mag), li, True)
    endOfDirectory(plugin.handle)


@plugin.route('/search_rarbg')
def rarbg_search():
    keyboard = xbmc.Keyboard('', 'Search')
    keyboard.doModal()
    if keyboard.isConfirmed():
        keyboardinput = keyboard.getText()
        if keyboardinput:
            try:
                t = torapi()
                for f in t.search(keyboardinput):
                    addDirectoryItem(plugin.handle, plugin.url_for(
                        show_torrent, ih='add', magnet=f['download']), ListItem(f['filename']), True)
                endOfDirectory(plugin.handle)
            except Exception as e:
                kodiutils.notification("rarbg", str(e))
                return


def run():
    plugin.run()
