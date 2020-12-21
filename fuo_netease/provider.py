import logging

from feeluown.library import AbstractProvider, ProviderV2, ProviderFlags
from feeluown.models import ModelType
from .api import API


logger = logging.getLogger(__name__)


class NeteaseProvider(AbstractProvider, ProviderV2):
    class meta:
        identifier = 'netease'
        name = '网易云音乐'
        flags = {
            ModelType.song: ProviderFlags.similar,
        }

    def __init__(self):
        super().__init__()
        self.api = API()

    @property
    def identifier(self):
        return 'netease'

    @property
    def name(self):
        return '网易云音乐'

    def auth(self, user):
        assert user.cookies is not None
        self._user = user
        self.api.load_cookies(user.cookies)

    def song_list_similar(self, song):
        songs = self.api.get_similar_song(song.identifier)
        return [_deserialize(song, NeteaseSongSchema) for song in songs]


provider = NeteaseProvider()


from .models import search, _deserialize  # noqa
from .schemas import NeteaseSongSchema
provider.search = search
