import asyncio
import logging
import os
from typing import TYPE_CHECKING, Protocol

from feeluown.utils import aio
from feeluown.gui.provider_ui import (
    AbstractProviderUi,
    UISupportsLoginOrGoHome,
)

from .excs import NeteaseIOError
from .provider import provider
from .login_controller import LoginController
from .ui import LoginDialog

if TYPE_CHECKING:
    from feeluown.app.gui_app import GuiApp

logger = logging.getLogger(__name__)


class UISupports(UISupportsLoginOrGoHome, Protocol):
    ...


class NeteaseProviderUI(AbstractProviderUi):
    """
    FIXME: 简化 login_as 和 ready_to_login 两个方法的实现逻辑
    """

    def __init__(self, app: 'GuiApp'):
        self._app = app
        self.login_dialog = LoginDialog(
            verify_captcha=LoginController.check_captcha,
            verify_userpw=LoginController.check,
            create_user=LoginController.create,
        )
        self._user = None

    def _(self) -> UISupports:
        return self

    @property
    def provider(self):
        return provider

    def get_colorful_svg(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'assets', 'icon.svg')

    def register_pages(self, route):
        from .page_fav import render as fav_render  # noqa

        route('/providers/netease/fav')(fav_render)

    def login_or_go_home(self):
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
        left_panel.playlists_con.create_btn.show()
        left_panel.my_music_con.show()

        mymusic_fm_item = self._app.mymusic_uimgr.create_item('私人 FM')
        mymusic_fm_item.clicked.connect(self._activate_fm)
        mymusic_cloud_item = self._app.mymusic_uimgr.create_item('云盘歌曲')
        mymusic_cloud_item.clicked.connect(
            lambda: self._app.browser.goto(page='/providers/netease/fav'),
            weak=False)

        self._app.mymusic_uimgr.clear()
        self._app.mymusic_uimgr.add_item(mymusic_fm_item)
        self._app.mymusic_uimgr.add_item(mymusic_cloud_item)

        await self._refresh_current_user_playlists()

    async def _refresh_current_user_playlists(self):
        playlists, fav_playlists = await aio.run_fn(self.provider.current_user_playlists)
        self._app.pl_uimgr.clear()
        self._app.pl_uimgr.add(playlists)
        self._app.pl_uimgr.add(fav_playlists, is_fav=True)

    def _activate_fm(self):
        self._app.fm.activate(self._fetch_fm_songs)

    def _fetch_fm_songs(self, *args, **kwargs):
        songs = provider.current_user_get_radio_songs()  # noqa
        if songs is None:
            raise NeteaseIOError('unknown error: get no radio songs')
        return songs
