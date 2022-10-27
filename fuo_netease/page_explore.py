import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QHBoxLayout,
)

from feeluown.utils import aio
from feeluown.utils.reader import wrap, create_reader
from feeluown.gui.widgets.playlist import PlaylistListView, PlaylistListModel, \
    PlaylistFilterProxyModel
from feeluown.gui.widgets.textbtn import TextButton
from feeluown.gui.helpers import fetch_cover_wrapper, BgTransparentMixin
from feeluown.gui.widgets.song_minicard_list import SongMiniCardListModel, \
    SongMiniCardListView, SongMiniCardListDelegate


async def render(req, **kwargs):
    app = req.ctx['app']
    provider = app.library.get('netease')

    scroll_area = ScrollArea()
    view = HomeView()
    scroll_area.setWidget(view)
    app.ui.right_panel.set_body(scroll_area)

    songs = await aio.run_fn(lambda: provider._user.rec_songs)
    view.daily_songs_view.setModel(
        SongMiniCardListModel(create_reader(songs), fetch_cover_wrapper(app)))
    view.daily_songs_view.play_song_needed.connect(
        app.playlist.play_model)

    playlists = await aio.run_fn(lambda: provider._user.rec_playlists)
    model = PlaylistListModel(wrap(playlists),
                              fetch_cover_wrapper(app),
                              {p.identifier: p.name for p in app.library.list()})
    filter_model = PlaylistFilterProxyModel()
    filter_model.setSourceModel(model)
    view.daily_rec_view.setModel(filter_model)
    view.daily_rec_view.show_playlist_needed.connect(
        lambda model: app.browser.goto(model=model))


class ScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        if sys.platform.lower() != 'darwin':
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

class HeaderLabel(QLabel):
    def __init__(self, text=None):
        super().__init__(text=None)

        self.setTextFormat(Qt.RichText)


class HomeView(QWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.header_title = HeaderLabel()
        self.header_daily_songs = HeaderLabel()
        self.header_daily_rec = HeaderLabel()
        self.daily_songs_view = SongMiniCardListView(
            row_height=60,
            no_scroll_v=True,
            fixed_row_count=3,
        )
        self.daily_songs_view.setItemDelegate(
            SongMiniCardListDelegate(
                self.daily_songs_view,
                card_min_width=210,
                card_height=50,
                card_v_spacing=10,
            ))
        self.daily_rec_view = PlaylistListView(
            img_min_width=100,
            no_scroll_v=True,
            fixed_row_count=2,
        )

        self.header_title.setText('<h2>网易云音乐</h2>')
        self.header_daily_songs.setText('<h3>每日歌曲推荐</h3>')
        self.header_daily_rec.setText('<h3>每日推荐</h3>')

        self._layout = QVBoxLayout(self)
        self._setup_ui()

    def _setup_ui(self):
        self._layout.setContentsMargins(20, 10, 20, 0)
        self._layout.setSpacing(0)

        self._layout.addWidget(self.header_title)
        self._layout.addSpacing(30)
        self._layout.addWidget(self.header_daily_songs)
        self._layout.addWidget(self.daily_songs_view)
        self._layout.addSpacing(10)
        self._layout.addWidget(self.header_daily_rec)
        self._layout.addWidget(self.daily_rec_view)
        self._layout.addStretch(1)