# -*- coding: utf-8 -*-

import routing
import logging
import xbmcaddon
import requests
from xml.etree import ElementTree
from urlparse import urlparse
from urlparse import parse_qs

from resources.lib import kodiutils
from resources.lib import kodilogging
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory
from os import path

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))
kodilogging.config()
plugin = routing.Plugin()

def str_url(sec):
    p = path.join(kodiutils.get_setting('server'), sec)
    logger.info(p)
    return p


def ping():
    try:
        req = requests.get(str_url('ping'))
        req.raise_for_status()
        return True
    except Exception as e:
        kodiutils.notification("Cannot connect to server", str(e))
        return False

@plugin.route('/')
def index():
    if not ping():
        kodiutils.show_settings()
        return
    addDirectoryItem(plugin.handle, plugin.url_for(show_torrents), ListItem('Torrents'), True)
    addDirectoryItem(plugin.handle, plugin.url_for(show_videos), ListItem('Videos'), True)
    addDirectoryItem(plugin.handle, plugin.url_for(show_shows_all), ListItem('Shows'), True)
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
            #ih = t.find('{http://showrss.info}info_hash').text
            ih = parse_qs(urlparse(ih).query).get('xt')[0].replace('urn:btih:', '')
            addDirectoryItem(plugin.handle, plugin.url_for(show_torrent, ih), ListItem(title), True)
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
def show_torrent(ih):
    try:
        req = requests.get(str_url('torrent/{}'.format(ih)))
        req.raise_for_status()
        for f in req.json()['files']:
            addDirectoryItem(plugin.handle, "{}{}".format(kodiutils.get_setting('server'), f['data']), ListItem('/'.join(f['Path'])))
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

def run():
    plugin.run()
