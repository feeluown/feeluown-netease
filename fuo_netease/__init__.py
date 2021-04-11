# -*- coding: utf-8 -*-

import logging
import os

from .provider import provider

__alias__ = '网易云音乐'
__feeluown_version__ = '2.1a0'
__version__ = '0.0.2'
__desc__ = '网易云音乐'

logger = logging.getLogger(__name__)


def enable(app):
    app.library.register(provider)
    if app.mode & app.GuiMode:
        from .nem import Nem

        nem = Nem(app)
        nem.initialize()
        item = app.pvd_uimgr.create_item(
            name=provider.identifier,
            text='网易云音乐',
            desc='点击可以登录',
            colorful_svg=os.path.abspath(
                os.path.join(os.path.dirname(__file__), 'assets', 'icon.svg')
            ),
        )
        item.clicked.connect(nem.ready_to_login)
        nem._pm = item
        app.pvd_uimgr.add_item(item)


def disable(app):
    app.library.deregister(provider)
    if app.mode & app.GuiMode:
        app.provider_uimgr.remove(provider.identifier)
