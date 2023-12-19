from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from feeluown.utils.reader import create_reader
from feeluown.utils.aio import run_fn
from feeluown.gui.widgets.header import LargeHeader, MidHeader
from feeluown.gui.widgets.playlist import PlaylistListView, PlaylistListModel, \
    PlaylistFilterProxyModel
from feeluown.gui.widgets.textbtn import TextButton
from feeluown.gui.helpers import fetch_cover_wrapper, BgTransparentMixin
from feeluown.gui.widgets.song_minicard_list import (
    SongMiniCardListView,
    SongMiniCardListModel,
    SongMiniCardListDelegate,
)

from fuo_netease import provider


if TYPE_CHECKING:
    from feeluown.app.gui_app import GuiApp


async def render(req, **kwargs):
    app: 'GuiApp' = req.ctx['app']

    playlists = provider.current_user_rec_playlists_p
    view = ExploreView(app)
    await view.show_daily_rec_songs()

    model = PlaylistListModel(create_reader(playlists),
                              fetch_cover_wrapper(app),
                              {p.identifier: p.name for p in app.library.list()})
    filter_model = PlaylistFilterProxyModel()
    filter_model.setSourceModel(model)
    view.playlist_list_view.setModel(filter_model)
    view.playlist_list_view.show_playlist_needed.connect(
        lambda model: app.browser.goto(model=model))
    app.ui.right_panel.set_body(view)


class _PlaylistListView(PlaylistListView, BgTransparentMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, no_scroll_v=True, **kwargs)
        BgTransparentMixin.__init__(self)
        self.setWrapping(False)


class ExploreView(QWidget):
    def __init__(self, app):
        super().__init__(parent=None)
        self._app = app

        self.header_title = LargeHeader()
        self.header_playlist_list = MidHeader()
        self.header_daily_rec = MidHeader()
        self.playlist_list_view = _PlaylistListView(img_min_width=100)

        self.daily_rec_view = SongMiniCardListView(no_scroll_v=False)
        delegate = SongMiniCardListDelegate(
            self.daily_rec_view,
            card_min_width=150,
            card_height=40,
            card_padding=(5 + SongMiniCardListDelegate.img_padding, 5, 0, 5),
            card_right_spacing=10,
        )
        self.daily_rec_view.setItemDelegate(delegate)

        self.header_title.setText('发现音乐')
        self.header_playlist_list.setText('个性化推荐')
        self.header_daily_rec.setText('每日推荐')

        self._layout = QVBoxLayout(self)
        self._setup_ui()

        self.daily_rec_view.play_song_needed.connect(self._app.playlist.play_model)

    def _setup_ui(self):
        self._layout.setContentsMargins(20, 10, 20, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.header_title)
        self._layout.addSpacing(10)
        self._layout.addWidget(self.header_daily_rec)
        self._layout.addSpacing(5)
        self._layout.addWidget(self.daily_rec_view)
        self._layout.addSpacing(20)
        self._layout.addWidget(self.header_playlist_list)
        self._layout.addWidget(self.playlist_list_view)
        self._layout.addStretch(0)

    async def show_daily_rec_songs(self):
        songs = await run_fn(lambda: provider.current_user_rec_songs_p)
        model = SongMiniCardListModel(create_reader(songs),
                                      fetch_cover_wrapper(self._app))
        self.daily_rec_view.setModel(model)
