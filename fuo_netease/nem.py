import asyncio
import logging

from PyQt5.QtCore import QObject

from feeluown.utils import aio
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

    def initialize(self):
        from .page_explore import render as explore_render # noqa
        from .page_fav import render as fav_render  # noqa
        from .page_daily_recommendation import render as dr_render

        self._app.browser.route('/providers/netease/explore')(explore_render)
        self._app.browser.route('/providers/netease/fav')(fav_render)
        self._app.browser.route('/providers/netease/daily_recommendation')(dr_render)

    def ready_to_login(self):
        if self._user is not None:
            logger.debug('You have already logined in.')
            asyncio.ensure_future(self.login_as(self._user))
            return

        logger.debug('Trying to load last login user...')
        user = LoginController.load()
        if user is not None:
            cookies, exists = user.cache_get('cookies')
            assert exists
            if 'MUSIC_U' in cookies:
                logger.debug('Trying to load last login user...done')
                asyncio.ensure_future(self.login_as(user))
                return

        logger.debug('Trying to load last login user...failed')
        self.login_dialog.show()
        self.login_dialog.load_user_pw()
        self.login_dialog.login_success.connect(
            lambda user: asyncio.ensure_future(self.login_as(user)))

    async def login_as(self, user):
        provider.auth(user)
        self._user = user
        LoginController.save(user)
        left_panel = self._app.ui.left_panel
        left_panel.playlists_con.show()
        left_panel.my_music_con.show()

        mymusic_explore_item = self._app.mymusic_uimgr.create_item('🎵 发现音乐')
        mymusic_explore_item.clicked.connect(
            lambda: self._app.browser.goto(page='/providers/netease/explore'),
            weak=False)
        mymusic_fm_item = self._app.mymusic_uimgr.create_item('📻 私人 FM')
        mymusic_fm_item.clicked.connect(self.activate_fm)
        mymusic_fav_item = self._app.mymusic_uimgr.create_item('♥ 收藏与关注')
        mymusic_fav_item.clicked.connect(
            lambda: self._app.browser.goto(page='/providers/netease/fav'),
            weak=False)

        self._app.mymusic_uimgr.clear()
        self._app.mymusic_uimgr.add_item(mymusic_explore_item)
        self._app.mymusic_uimgr.add_item(mymusic_fm_item)
        self._app.mymusic_uimgr.add_item(mymusic_fav_item)

        playlists, fav_playlists = await aio.run_fn(provider.current_user_playlists)
        self._app.pl_uimgr.clear()
        self._app.pl_uimgr.add(playlists)
        self._app.pl_uimgr.add(fav_playlists, is_fav=True)

    def activate_fm(self):
        self._app.fm.activate(self.fetch_fm_songs)

    def fetch_fm_songs(self, *args, **kwargs):
        songs = provider.current_user_get_radio_songs()  # noqa
        if songs is None:
            raise NeteaseIOError('unknown error: get no radio songs')
        return songs
