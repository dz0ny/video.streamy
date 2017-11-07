# -*- coding: utf-8 -*-

import re
from urllib import quote_plus, unquote, urlencode
from urlparse import parse_qs, urlparse
from xml.etree import ElementTree

import requests

import xbmc
from xbmcplugin import setContent
from resources.lib.api import Streamy, fetchapi, torapi
from resources.lib.notify import OverlayText
from simpleplugin import Plugin

app = Plugin()
streamy = Streamy(app.get_setting('server'))


def search_ui():
    keyboard = xbmc.Keyboard('', 'Search')
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText()

def search_trailer(title):
    title = quote_plus(title)    
    return 'Container.Update(plugin://plugin.video.youtube/kodion/search/query/?q={})'.format(title)


def inspect_url(title, magnet):
    parts = re.split(r'[\W\-]+', title)
    quas = ['720p', '1080p', 'hdrip', 'webrip',
            'dvrip', 'web-dl', 'web', 'hdtv']
    q = []
    for part in parts:
        q.append(part)
        if part.encode('ascii').lower() in quas:
            break
        
    title = ' '.join(q)
    return {
        'label': title,
        'url': app.get_url(action='inspect_torrent', magnet=magnet),
        'context_menu': [
            ('Download', 'Action'),
            ('Trailer', search_trailer(title)),
        ],
    }


def directory(title, action):
    return {
        'label': title,
        'url': app.get_url(action=action),
    }


@app.action()
def root():
    yield directory('Downloaded', 'downloaded')
    yield directory('ShowRSS', 'showrss')
    yield directory('RarBG', 'rarbg')
    yield directory('PopcornTime', 'popcorntime')

@app.action()
def downloaded():
    for name, ih in streamy.torrents():
        yield {
            'label': name,
            'url': app.get_url(action='inspect_torrent', ih=ih),
            'context_menu': [
                ('Download', 'Action'),
                ('Delete', 'Action'),
            ],
        }

@app.cached(60)
@app.action()
def showrss():
    ss_id = app.get_setting('showrss_id')
    if ss_id != '':
        url = 'http://showrss.info/user/{}.rss?magnets=true&namespaces=true&name=clean&quality=null&re=null'.format(
            ss_id)
    else:
        url = 'https://showrss.info/other/all.rss'
    req = requests.get(url)
    req.raise_for_status()
    tree = ElementTree.fromstring(req.content)
    for t in tree.iter('item'):
        name = t.find('title').text
        magnet = t.find('link').text
        yield inspect_url(name, magnet)

@app.action()
def inspect_torrent(params):
    if 'ih' in params:
        torrent = streamy.torrent(params.ih)
    else:
        torrent = streamy.torrent(None, params.magnet)
    for name, url, size in torrent:
        yield {
            'label': name,
            'url': url,
            'is_playable': True,
        }


@app.action()
def rarbg():
    
    def url(cat):
        return app.get_url(action='rarbg_category', category=cat)

    yield {'label': 'Movies', 'url': url('movies')}
    yield {'label': 'TV', 'url': url('tv')}
    yield {'label': 'Music', 'url': url('23;24;25;26')}
    yield {'label': 'XXX', 'url': url('4')}


@app.cached(60)
@app.action()
def rarbg_category(params):
    torrents = torapi().category(params.category)
    for name, url in torrents:
        yield inspect_url(name, url)


@app.action()
def popcorntime():
    
    def url_movie(sort, limit, search=False):
        return app.get_url(
            action='popcorntime_movie',
            sort=sort,
            limit=limit,
            search=search,
        )
    
    def url_tv(sort, limit, search=False):
        return app.get_url(
            action='popcorntime_tv',
            sort=sort,
            limit=limit,
            search=search,
        )

    yield {'label': 'Movies', 'url': url_movie('year', 50)}
    yield {'label': 'Movies - Search', 'url': url_movie('year', 2, 'ok')}
    yield {'label': 'Movies - New', 'url': url_movie('last added', 5)}
    yield {'label': 'Movies - Trending', 'url': url_movie('trending', 5)}
    yield {'label': 'Movies - Rating', 'url': url_movie('rating', 5)}
    yield {'label': 'TV', 'url': url_tv('year', 50)}
    yield {'label': 'TV- Search', 'url': url_tv('year', 2, 'ok')}
    yield {'label': 'TV - New', 'url': url_tv('last added', 5)}
    yield {'label': 'TV - Trending', 'url': url_tv('trending', 5)}
    yield {'label': 'TV - Rating', 'url': url_tv('rating', 5)}


@app.action()
def popcorntime_tv(params):
    setContent(app._handle, 'tvshows')
    search = None
    if params.search=='ok':
        search = search_ui()
    shows = fetchapi().get_shows(params.sort, int(params.limit), search)
    def url_show(show):
        return app.get_url(
            action='popcorntime_show',
            show=show,
        )
    for show in shows:
        yield {
            'label': show['title'],
            'poster': show['images']['poster'],
            'fanart': show['images']['fanart'],
             'url': url_show(show['imdb_id'])
        }


@app.action()
def popcorntime_show(params):
    setContent(app._handle, 'episodes')
    show = fetchapi().get_show(params.show)
    episodes = sorted(show['episodes'], key=lambda f: (
        10000 * int(f['season'])) + int(f['episode']))
    for f in episodes:
        name = '{} S{:02d}E{:02d}: {}'.format(
            show['title'], int(f['season']), int(f['episode']), f['title']
        )
        for k, v in f['torrents'].iteritems():
            url = v['url']
            break
        data = inspect_url(name, url)
        data['info'] = {
            'video': {
                'year': int(f['year']),
                'duration': int(f['runtime']) * 60,
                'plot': f['synopsis'],
            }
        }
        yield data



@app.cached(60)
@app.action()
def popcorntime_movie(params):
    search = None
    if params.search=='ok':
        search = search_ui()
    setContent(app._handle, 'movies')
    torrents = fetchapi().get_movies(params.sort, int(params.limit), search)
    for f in torrents:
        torrents = f['torrents']['en']
        try:
            mag = torrents['720p']['url']
            mag = torrents['1080p']['url']
        except Exception:
            for k, v in torrents.iteritems():
                mag = v['url']
                break
        data = inspect_url(f['title'], mag)
        data['info'] = {
            'video': {
                'genre': '/'.join(f['genres']),
                'year': int(f['year']),
                'duration': int(f['runtime']) * 60,
                'plot': f['synopsis'],
            }
        }
        data['poster'] = f['images']['poster']
        data['fanart'] = f['images']['fanart']
        data['online_db_ids'] = {'imdb': f['imdb_id']}
        data['ratings'] = [{
            'type': 'imdb',
            'rating': f['rating']['percentage']
        }]
        yield data


def start():
    app.run()
