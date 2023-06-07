from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout

from feeluown.utils.reader import wrap
from feeluown.gui.widgets.playlist import PlaylistListView, PlaylistListModel, \
    PlaylistFilterProxyModel
from feeluown.gui.widgets.textbtn import TextButton
from feeluown.gui.helpers import fetch_cover_wrapper, BgTransparentMixin

from fuo_netease import provider


async def render(req, **kwargs):
    app = req.ctx['app']

    playlists = provider.current_user_rec_playlists_p
    view = ExploreView()
    view.daily_rec_btn.clicked.connect(
        lambda: app.browser.goto(page='/providers/netease/daily_recommendation'))
    model = PlaylistListModel(wrap(playlists),
                              fetch_cover_wrapper(app),
                              {p.identifier: p.name for p in app.library.list()})
    filter_model = PlaylistFilterProxyModel()
    filter_model.setSourceModel(model)
    view.playlist_list_view.setModel(filter_model)
    view.playlist_list_view.show_playlist_needed.connect(
        lambda model: app.browser.goto(model=model))
    app.ui.right_panel.set_body(view)


class HeaderLabel(QLabel):
    def __init__(self):
        super().__init__()

        self.setTextFormat(Qt.RichText)
        # Margin is same as playlist list view CoverSpacing
        self.setIndent(20)


class _PlaylistListView(PlaylistListView, BgTransparentMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, no_scroll_v=True, **kwargs)
        BgTransparentMixin.__init__(self)


class ExploreView(QWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.header_title = HeaderLabel()
        self.header_playlist_list = HeaderLabel()
        self.header_daily_rec = HeaderLabel()
        self.playlist_list_view = _PlaylistListView(img_min_width=100)
        self.daily_rec_btn = TextButton('查看每日推荐')

        self.header_title.setText('<h1>发现音乐</h1>')
        self.header_playlist_list.setText('<h2>个性化推荐</h2>')
        self.header_daily_rec.setText('<h2>每日推荐</h2>')

        self._daily_rec_layout = QHBoxLayout()
        self._layout = QVBoxLayout(self)
        self._setup_ui()

    def _setup_ui(self):
        self.playlist_list_view.setWrapping(False)

        self._layout.setContentsMargins(0, 10, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.header_title)
        self._layout.addSpacing(30)
        self._layout.addWidget(self.header_daily_rec)
        self._layout.addSpacing(5)
        self._layout.addLayout(self._daily_rec_layout)
        self._layout.addSpacing(20)
        self._layout.addWidget(self.header_playlist_list)
        self._layout.addWidget(self.playlist_list_view)
        self._layout.addStretch(0)

        # NOTE(cosven): 人肉设置一个 25 的间距，在 macOS 看起来勉强还行
        self._daily_rec_layout.addSpacing(25)
        self._daily_rec_layout.addWidget(self.daily_rec_btn)
        self._daily_rec_layout.addStretch(0)
