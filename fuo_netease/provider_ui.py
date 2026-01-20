import logging
import os
from typing import TYPE_CHECKING, Protocol

from feeluown.utils.dispatch import Signal
from feeluown.gui.provider_ui import (
    AbstractProviderUi,
    UISupportsLoginOrGoHome,
    NavBtn,
)
from feeluown.gui.widgets.login import (
    CookiesLoginDialog as _CookiesLoginDialog, InvalidCookies,
)

from .provider import provider
from .login_controller import LoginController

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
        self._user = None
        self._login_event = Signal()

    def _(self) -> UISupports:
        return self

    @property
    def login_event(self):
        return self._login_event

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
            self.login_event.emit(self, 2)
            return

        logger.debug('Trying to load last login user...')
        user = LoginController.load()
        if user is not None:
            cookies, exists = user.cache_get('cookies')
            assert exists
            if 'MUSIC_U' in cookies:
                logger.debug('Trying to load last login user...done')
                self.provider.auth(user)
                self.login_event.emit(self, 1)
                return

        logger.debug('Trying to load last login user...failed')
        self._dialog = CookiesLoginDialog('https://music.163.com', ['MUSIC_U'])
        self._dialog.login_succeed.connect(self.on_login_succeed)
        self._dialog.show()
        self._dialog.autologin()

    def on_login_succeed(self):
        del self._dialog
        self.login_event.emit(self, 1)

    def list_nav_btns(self):
        return [
            NavBtn(
                icon='☁️',
                text='云盘歌曲',
                cb=lambda: self._app.browser.goto(page='/providers/netease/fav')
            ),
        ]


class CookiesLoginDialog(_CookiesLoginDialog):

    def setup_user(self, user):
        provider.auth(user)

    async def user_from_cookies(self, cookies):
        try:
            user = provider.get_user_from_cookies(cookies)
        except ValueError as e:
            raise InvalidCookies(str(e))
        return user

    def load_user_cookies(self):
        user = LoginController.load()
        if user is not None:
            cookies, exists = user.cache_get('cookies')
            assert exists
            return cookies
        return None

    def dump_user_cookies(self, user, cookies):
        LoginController.save(user)
