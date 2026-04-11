# -*- coding: utf-8 -*-

import logging

from .provider import provider
from consts import domain

__alias__ = '网易云音乐'
__feeluown_version__ = '2.1a0'
__version__ = '0.0.2'
__desc__ = '网易云音乐'

logger = logging.getLogger(__name__)


def enable(app):
    try:
        from pathlib import Path
        from feeluown.i18n import register_plugin_i18n
        locales_dir = Path(__file__).parent / "locales"
        resource_ids = ["main.ftl"]
        register_plugin_i18n(domain=domain, locales_dir=locales_dir,
                             resource_ids=resource_ids)
    except ImportError:
        logger.warning("The latest version of FeelUOwn isn't installed, "
                       "update FeelUOwn for localization support!")
    app.library.register(provider)
    if app.mode & app.GuiMode:
        from .provider_ui import NeteaseProviderUI
        provider_ui = NeteaseProviderUI(app)
        app.pvd_ui_mgr.register(provider_ui)


def disable(app):
    app.library.deregister(provider)
    if app.mode & app.GuiMode:
        app.provider_uimgr.remove(provider.identifier)
