import logging

from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from feeluown.gui.widgets import TextButton
from feeluown.utils import aio
from feeluown.gui.base_renderer import LibraryTabRendererMixin
from feeluown.gui.page_containers.table import Renderer
from feeluown.gui.widgets.tabbar import Tab

from fuo_netease import provider

logger = logging.getLogger(__name__)


async def render(req, **kwargs):
    app = req.ctx['app']
    app.ui.right_panel.set_body(app.ui.table_container)

    tab_id = Tab(int(req.query.get('tab_id', Tab.songs.value)))
    # FIXM
    renderer = FavRenderer(tab_id)
    await app.ui.table_container.set_renderer(renderer)


class FavRenderer(Renderer, LibraryTabRendererMixin):
    def __init__(self, tab_id):
        global provider

        self.tab_id = tab_id
        self._user = provider._user

    async def render(self):
        self.render_tabbar()
        self.meta_widget.show()
        self.meta_widget.title = '收藏与关注'

        if self.tab_id == Tab.songs:
            self.show_songs(await aio.run_fn(provider.current_user_cloud_songs))
            dir_upload_btn = TextButton('上传目录', self.toolbar)
            dir_upload_btn.clicked.connect(
                lambda: aio.run_afn(self._upload_cloud_songs_bydir))
            self.toolbar.add_tmp_button(dir_upload_btn)
            upload_btn = TextButton('上传音乐', self.toolbar)
            upload_btn.clicked.connect(lambda: aio.run_afn(self._upload_cloud_songs))
            self.toolbar.add_tmp_button(upload_btn)
            refresh_btn = TextButton('刷新音乐', self.toolbar)
            refresh_btn.clicked.connect(self._refresh_cloud_songs)
            self.toolbar.add_tmp_button(refresh_btn)
        elif self.tab_id == Tab.albums:
            self.show_albums(await aio.run_fn(provider.current_user_fav_albums))
        elif self.tab_id == Tab.artists:
            self.show_artists(await aio.run_fn(provider.current_user_fav_artists))
        elif self.tab_id == Tab.playlists:
            playlists = await aio.run_fn(provider.current_user_fav_djradios)
            self.show_playlists(playlists)

    async def _upload_cloud_songs_bydir(self):
        # FIXME: 目前无法根据当前页面进行自动刷新, 只能手动刷新
        # FIXME: 本地音乐还没扫描完成或歌曲播放时, 可能线程错误提示
        root = QFileDialog.getExistingDirectory(
            self.toolbar, '选择文件夹', Path.home().as_posix())
        if root == '':
            return

        import os
        paths = []
        for dir, _, files in os.walk(root):
            exts = ['mp3', 'm4a', 'wma', 'flac', 'ogg']
            paths.extend([os.path.join(dir, f)
                          for f in sorted(files)
                          if f.rsplit('.', 1)[-1] in exts])

        for idx, path in enumerate(paths):
            ok = await aio.run_fn(self._user.meta.provider.upload_song, path)
            if ok:
                logger.warning(f'[{idx + 1}/{len(paths)}]{path} 上传成功!')
            else:
                logger.warning(f'[{idx + 1}/{len(paths)}]{path} 上传失败!')
        QMessageBox.information(self.toolbar, '上传目录', '上传完成！')

    async def _upload_cloud_songs(self):
        # FIXME: 目前无法根据当前页面进行自动刷新, 只能手动刷新
        # FIXME: 本地音乐还没扫描完成或歌曲播放时, 可能线程错误提示
        paths, _ = QFileDialog.getOpenFileNames(
            self.toolbar, '选择文件', Path.home().as_posix(),
            'Supported Files (*.mp3 *.m4a *.wma *.flac *.ogg);; All Files (*.*)')
        if not paths:
            return

        for idx, path in enumerate(paths):
            ok = await aio.run_fn(self._user.meta.provider.upload_song, path)
            if ok:
                logger.warning(f'[{idx + 1}/{len(paths)}]{path} 上传成功!')
            else:
                logger.warning(f'[{idx + 1}/{len(paths)}]{path} 上传失败!')
        QMessageBox.information(self.toolbar, '上传音乐', '上传完成！')

    def _refresh_cloud_songs(self):
        self.show_by_tab_id(Tab.songs)

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
            self.tabbar.playlists_btn.setText('收藏的电台')
        except Exception as e:
            logger.warning(str(e))
