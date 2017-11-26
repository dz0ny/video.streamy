import os
import xbmc
import xbmcgui

XBFONT_CENTER_X = 0x00000002
XBFONT_CENTER_Y = 0x00000004
WINDOW_FULLSCREEN_VIDEO = 12005
VIEWPORT_WIDTH = 1920.0
VIEWPORT_HEIGHT = 1088.0
OVERLAY_WIDTH = int(VIEWPORT_WIDTH * 0.7)  # 70% size
OVERLAY_HEIGHT = 150
ADDON_PATH= '/home/dz0ny/Namizje/plugin.video.quasar-master'
class OverlayText(object):
    def __init__(self, w=OVERLAY_WIDTH, h=OVERLAY_HEIGHT, *args, **kwargs):
        self.window = xbmcgui.Window(WINDOW_FULLSCREEN_VIDEO)
        viewport_w, viewport_h = self._get_skin_resolution()
        # Adjust size based on viewport, we are using 1080p coordinates
        w = int(w * viewport_w / VIEWPORT_WIDTH)
        h = int(h * viewport_h / VIEWPORT_HEIGHT)
        x = (viewport_w - w) / 2
        y = (viewport_h - h) / 2 + 10
        self._shown = False
        self._text = ""
        self._label = xbmcgui.ControlLabel(x, y, w, h, self._text,
                                           alignment=XBFONT_CENTER_X | XBFONT_CENTER_Y, *args, **kwargs)
        self._shadow = xbmcgui.ControlLabel(x + 1, y + 1, w, h, self._text,
                                            textColor='0xD0000000',
                                            alignment=XBFONT_CENTER_X | XBFONT_CENTER_Y, *args, **kwargs)
        self._background = xbmcgui.ControlImage(x, y, w, h, os.path.join(ADDON_PATH, "resources", "img", "black.png").encode('utf-8'))
        self._background.setColorDiffuse("0xD0000000")

    def show(self):
        if not self._shown:
            self.window.addControls([self._background, self._shadow, self._label])
            self._shown = True

    def hide(self):
        if self._shown:
            self._shown = False
            self.window.removeControls([self._background, self._shadow, self._label])

    def close(self):
        self.hide()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        self._text = text
        if self._shown:
            self._shadow.setLabel(self._text)
            self._label.setLabel(self._text)

    # This is so hackish it hurts.
    def _get_skin_resolution(self):
        import xml.etree.ElementTree as ET
        skin_path = xbmc.translatePath("special://skin/")
        tree = ET.parse(os.path.join(skin_path, "addon.xml"))
        res = tree.findall("./extension/res")[0]
        return int(res.attrib["width"]), int(res.attrib["height"])
