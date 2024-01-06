import logging

from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from feeluown.gui.widgets import TextButton
from feeluown.utils import aio
from feeluown.gui.page_containers.table import Renderer

from fuo_netease import provider

logger = logging.getLogger(__name__)


async def render(req, **kwargs):
    app = req.ctx['app']
    app.ui.right_panel.set_body(app.ui.table_container)

    renderer = FavRenderer()
    await app.ui.table_container.set_renderer(renderer)


class FavRenderer(Renderer):
    def __init__(self):
        global provider

        self._user = provider._user

    async def render(self):
        self.meta_widget.show()
        self.meta_widget.title = '云盘'

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
            ok = await aio.run_fn(provider.upload_song, path)
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
            ok = await aio.run_fn(provider.upload_song, path)
            if ok:
                logger.warning(f'[{idx + 1}/{len(paths)}]{path} 上传成功!')
            else:
                logger.warning(f'[{idx + 1}/{len(paths)}]{path} 上传失败!')
        QMessageBox.information(self.toolbar, '上传音乐', '上传完成！')

    def _refresh_cloud_songs(self):
        self._app.browser.goto(page='/providers/netease/fav')
