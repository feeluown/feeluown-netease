from feeluown.utils.reader import wrap
from feeluown.gui.widgets.playlist import PlaylistListView, PlaylistListModel, \
    PlaylistFilterProxyModel
from feeluown.gui.page_containers.table import fetch_cover_wrapper


async def render(req, **kwargs):
    app = req.ctx['app']
    provider = app.library.get('netease')

    playlists = provider._user.rec_playlists
    view = PlaylistListView()
    model = PlaylistListModel(wrap(playlists), fetch_cover_wrapper(app.img_mgr))
    filter_model = PlaylistFilterProxyModel()
    filter_model.setSourceModel(model)
    view.setModel(filter_model)
    app.ui.right_panel.set_body(view)
