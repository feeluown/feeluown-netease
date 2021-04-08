from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

from feeluown.utils.reader import wrap
from feeluown.gui.widgets.playlist import PlaylistListView, PlaylistListModel, \
    PlaylistFilterProxyModel
from feeluown.gui.helpers import fetch_cover_wrapper, BgTransparentMixin


async def render(req, **kwargs):
    app = req.ctx['app']
    provider = app.library.get('netease')

    playlists = provider._user.rec_playlists
    view = ExploreView()
    model = PlaylistListModel(wrap(playlists),
                              fetch_cover_wrapper(app.img_mgr),
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
        self.playlist_list_view = _PlaylistListView(img_min_width=100)

        self.header_title.setText('<h1>发现音乐</h1>')
        self.header_playlist_list.setText('<h2>个性化推荐</h2>')

        self._layout = QVBoxLayout(self)
        self._setup_ui()

    def _setup_ui(self):
        self.playlist_list_view.setWrapping(False)

        self._layout.setContentsMargins(0, 10, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.header_title)
        self._layout.addSpacing(30)
        self._layout.addWidget(self.header_playlist_list)
        self._layout.addWidget(self.playlist_list_view)
        self._layout.addStretch(0)
