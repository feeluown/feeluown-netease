import asyncio
import logging

from PyQt5.QtCore import QObject

from .excs import NeteaseIOError
from .provider import provider
from .login_controller import LoginController
from .ui import LoginDialog


logger = logging.getLogger(__name__)


class Nem(QObject):
    """

    FIXME: 简化 login_as 和 ready_to_login 两个方法的实现逻辑
    """

    def __init__(self, app):
        super(Nem, self).__init__(parent=app)
        self._app = app
        self.login_dialog = LoginDialog(
            verify_captcha=LoginController.check_captcha,
            verify_userpw=LoginController.check,
            create_user=LoginController.create,
        )
        self._user = None
        self._pm = None

    def ready_to_login(self):
        if self._user is not None:
            logger.debug('You have already logined in.')
            asyncio.ensure_future(self.login_as(self._user))
            return
        logger.debug('Trying to load last login user...')
        user = LoginController.load()
        if user is None or 'MUSIC_U' not in user.cookies:
            logger.debug('Trying to load last login user...failed')
            self.login_dialog.show()
            self.login_dialog.load_user_pw()
            self.login_dialog.login_success.connect(
                lambda user: asyncio.ensure_future(self.login_as(user)))
        else:
            logger.debug('Trying to load last login user...done')
            asyncio.ensure_future(self.login_as(user))

    def show_fav_albums(self):
        self._app.ui.songs_table_container.show_albums_coll(self._user.fav_albums)

    def show_rec_songs(self):
        self._app.ui.songs_table_container.show_songs(self._user.rec_songs)

    async def login_as(self, user):
        provider.auth(user)
        self._user = user
        LoginController.save(user)
        left_panel = self._app.ui.left_panel
        left_panel.playlists_con.show()
        left_panel.my_music_con.show()

        mymusic_fm_item = self._app.mymusic_uimgr.create_item('📻 私人 FM')
        mymusic_fm_item.clicked.connect(self.activate_fm)
        mymusic_rec_item = self._app.mymusic_uimgr.create_item('📅 每日推荐')
        mymusic_rec_item.clicked.connect(self.show_rec_songs)
        mymusic_albums_item = self._app.mymusic_uimgr.create_item('♥ 我的专辑')
        mymusic_albums_item.clicked.connect(self.show_fav_albums)
        self._app.mymusic_uimgr.clear()
        self._app.mymusic_uimgr.add_item(mymusic_fm_item)
        self._app.mymusic_uimgr.add_item(mymusic_rec_item)
        self._app.mymusic_uimgr.add_item(mymusic_albums_item)

        loop = asyncio.get_event_loop()
        self._pm.text = '网易云音乐 - {}'.format(user.name)
        playlists = await loop.run_in_executor(None, lambda: user.playlists)
        self._app.pl_uimgr.clear()
        self._app.pl_uimgr.add(playlists)
        self._app.pl_uimgr.add(user.fav_playlists, is_fav=True)
        # self._app.pl_uimgr.add(user.rec_playlists)

    def activate_fm(self):
        self._app.fm.activate(self.fetch_fm_songs)

    def fetch_fm_songs(self, *args, **kwargs):
        songs = provider._user.get_radio()  # noqa
        if songs is None:
            raise NeteaseIOError('unknown error: get no radio songs')
        return songs
