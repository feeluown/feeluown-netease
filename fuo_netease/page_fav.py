import logging

from feeluown.utils import aio
from feeluown.gui.base_renderer import LibraryTabRendererMixin
from feeluown.gui.page_containers.table import Renderer
from feeluown.gui.widgets.tabbar import Tab


logger = logging.getLogger(__name__)


async def render(req, **kwargs):
    app = req.ctx['app']
    app.ui.right_panel.set_body(app.ui.table_container)

    provider = app.library.get('netease')
    tab_id = Tab(int(req.query.get('tab_id', Tab.songs.value)))
    # FIXM
    renderer = FavRenderer(tab_id, provider._user)
    await app.ui.table_container.set_renderer(renderer)


class FavRenderer(Renderer, LibraryTabRendererMixin):
    def __init__(self, tab_id, user):
        self.tab_id = tab_id
        self._user = user

    async def render(self):
        self.render_tabbar()
        self.meta_widget.show()
        self.meta_widget.title = '收藏与关注'

        if self.tab_id == Tab.songs:
            self.show_songs(await aio.run_fn(lambda: self._user.cloud_songs))
        elif self.tab_id == Tab.albums:
            self.show_albums(await aio.run_fn(lambda: self._user.fav_albums))
        elif self.tab_id == Tab.artists:
            self.show_artists(await aio.run_fn(lambda: self._user.fav_artists))

    def show_by_tab_id(self, tab_id):
        query = {'tab_id': tab_id.value}
        self._app.browser.goto(page='/providers/netease/fav', query=query)

    def render_tabbar(self):
        super().render_tabbar()

        # HACK: 使用一些私有接口，因为组件暴露的接口提供的能力非常有限
        try:
            self.tabbar.songs_btn.setText('云盘歌曲')
            self.tabbar.albums_btn.setText('收藏的专辑')
            self.tabbar.artists_btn.setText('关注的歌手')
            self.tabbar.videos_btn.hide()
            self.tabbar.playlists_btn.hide()
        except Exception as e:
            logger.warning(str(e))
