import logging

from marshmallow.exceptions import ValidationError

from feeluown.models import (
    cached_field,
    BaseModel,
    PlaylistModel,
    UserModel,
    SearchModel,
)
from feeluown.utils.reader import RandomSequentialReader, SequentialReader

from .provider import provider
from .excs import NeteaseIOError

logger = logging.getLogger(__name__)


def _deserialize(data, schema_cls):
    schema = schema_cls()
    obj = schema.load(data)
    return obj


def create_g(func, schema=None, data_field=None):
    data = func(limit=0)
    if data is None:
        raise NeteaseIOError('server responses with error status code')
    if data_field is None:
        data_field = 'data'

    count = int(data['count'])

    def read_func(start, end):
        data = func(start, end - start)
        return [_deserialize(data, schema)
                for data in data[data_field]]

    reader = RandomSequentialReader(count,
                                    read_func=read_func,
                                    max_per_read=200)
    return reader


def create_cloud_songs_g(func, func_extra, schema=None, schema_extra=None,
                         data_field=None, data_key=None):
    data = func(limit=0)
    if data is None:
        raise NeteaseIOError('server responses with error status code')
    if data_field is None:
        data_field = 'data'

    count = int(data['count'])

    def read_func(start, end):
        songs_data = func(start, end - start)

        songs = []
        extra_songs_info = []
        for idx, song_data in enumerate(songs_data[data_field]):
            if data_key:
                song_data = song_data[data_key]
            try:
                song = _deserialize(song_data, schema)
            except ValidationError:
                # FIXME: 有些云盘歌曲在 netease 上不存在，这时不能把它们转换成
                # SongModel。因为 SongModel 的逻辑没有考虑 song 不存在的情况。
                # 这类歌曲往往没有 ar/al 等字段，在反序列化的时候会报 ValidationError，
                # 所以这里如果检测到 ValidationError，就跳过这首歌曲。
                #
                # 可能的修复方法：
                # 1. 在 SongModel 上加一个 flag 来标识该歌曲是否为云盘歌曲，
                #    如果是的话，则使用 cloud_song_detail 接口来获取相关信息。
                # name = song_data['name']
                # logger.warn(f'cloud song:{name} may not exist on netease, skip it.')
                extra_songs_info.append((idx, song_data['id']))
                # song_data = func_extra(str(song_data['id']))[data_field][0]
                # song = _deserialize(song_data, schema_extra)
            else:
                songs.append(song)

        if extra_songs_info:
            extra_song_ids = ','.join([str(id) for (_, id) in extra_songs_info])
            extra_songs_data = func_extra(extra_song_ids)
            for idx, song_data in enumerate(extra_songs_data[data_field]):
                song = _deserialize(song_data, schema_extra)
                songs.insert(extra_songs_info[idx][0], song)

        return songs

    reader = RandomSequentialReader(count,
                                    read_func=read_func,
                                    max_per_read=200)
    return reader


class NBaseModel(BaseModel):
    # FIXME: remove _detail_fields and _api to Meta
    _api = provider.api

    class Meta:
        allow_get = True
        provider = provider


class NRadioModel(PlaylistModel, NBaseModel):
    class Meta:
        allow_create_songs_g = True

    def create_songs_g(self):
        data = self._api.djradio_list(self.identifier, limit=1, offset=0)
        count = data.get('count', 0)

        def g():
            offset = 0
            per = 50  # speed up first request
            while offset < count:
                tracks_data = self._api.djradio_list(
                    self.identifier, limit=per, offset=offset)
                for track_data in tracks_data.get('programs', []):
                    yield _deserialize(track_data, NDjradioSchema)
                offset += per

        return SequentialReader(g(), count)

    @classmethod
    def get(cls, identifier):
        data = cls._api.djradio_detail(identifier)
        radio = _deserialize(data, NDjradioSchema)
        return radio


class NSearchModel(SearchModel, NBaseModel):
    pass


class NUserModel(UserModel, NBaseModel):
    class Meta:
        fields = ('cookies',)
        fields_no_get = ('cookies', 'rec_songs', 'rec_playlists',
                         'fav_artists', 'fav_albums', )

    @classmethod
    def get(cls, identifier):
        user = {'id': identifier}
        user_brief = cls._api.user_brief(identifier)
        user.update(user_brief)
        playlists = cls._api.user_playlists(identifier)

        user['playlists'] = []
        user['fav_playlists'] = []
        for pl in playlists:
            if str(pl['userId']) == str(identifier):
                user['playlists'].append(pl)
            else:
                user['fav_playlists'].append(pl)
        # FIXME: GUI模式下无法显示歌单描述
        user = _deserialize(user, NeteaseUserSchema)
        return user

    @cached_field()
    def rec_playlists(self):
        playlists_data = self._api.get_recommend_playlists()
        rec_playlists = []
        for playlist_data in playlists_data:
            # FIXME: GUI模式下无法显示歌单描述
            playlist_data['coverImgUrl'] = playlist_data['picUrl']
            playlist_data['description'] = None
            playlist = _deserialize(playlist_data, V2PlaylistSchema)
            rec_playlists.append(playlist)
        return rec_playlists

    @property
    def fav_djradio(self):
        return create_g(self._api.subscribed_djradio, NeteaseDjradioSchema, 'djRadios')

    @fav_djradio.setter
    def fav_djradio(self, _):
        pass

    @property
    def fav_artists(self):
        return create_g(self._api.user_favorite_artists, V2BriefArtistSchema)

    @fav_artists.setter
    def fav_artists(self, _): pass

    @property
    def fav_albums(self):
        return create_g(self._api.user_favorite_albums, V2BriefAlbumSchema)

    @fav_albums.setter
    def fav_albums(self, _): pass

    @property
    def cloud_songs(self):
        return create_cloud_songs_g(
            self._api.cloud_songs,
            self._api.cloud_songs_detail,
            V2SongSchemaForV3,
            NCloudSchema,
            data_key='simpleSong'
        )

    @cloud_songs.setter
    def cloud_songs(self, _): pass

    # 根据过去经验，每日推荐歌曲在每天早上 6:00 刷新，
    # ttl 设置为 60s 是为了能够比较即时的获取今天推荐。
    @cached_field(ttl=60)
    def rec_songs(self):
        songs_data = self._api.get_recommend_songs()
        return [_deserialize(song_data, V2SongSchema)
                for song_data in songs_data]

    def get_radio(self):
        songs_data = self._api.get_radio_music()
        if songs_data is None:
            logger.error('data should not be None')
            return None
        return [_deserialize(song_data, V2SongSchema)
                for song_data in songs_data]


# import loop
from .schemas import (  # noqa
    V2SongSchema,
    V2BriefAlbumSchema,
    V2BriefArtistSchema,
    V2PlaylistSchema,
    NeteaseUserSchema,
    V2SongSchemaForV3,
    NDjradioSchema, NeteaseDjradioSchema, NCloudSchema,
)  # noqa
