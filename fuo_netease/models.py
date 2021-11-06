import logging

from marshmallow.exceptions import ValidationError

from feeluown.models import (
    cached_field,
    BaseModel,
    PlaylistModel,
    AlbumModel,
    ArtistModel,
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


class NBaseModel(BaseModel):
    # FIXME: remove _detail_fields and _api to Meta
    _api = provider.api

    class Meta:
        allow_get = True
        provider = provider


class NAlbumModel(AlbumModel, NBaseModel):

    @classmethod
    def get(cls, identifier):
        album_data = cls._api.album_infos(identifier)
        if album_data is None:
            return None
        album = _deserialize(album_data, NeteaseAlbumSchema)
        return album

    @property
    def desc(self):
        if self._desc is None:
            self._desc = self._api.album_desc(self.identifier)
        return self._desc

    @desc.setter
    def desc(self, value):
        self._desc = value


class NArtistModel(ArtistModel, NBaseModel):

    class Meta:
        allow_create_songs_g = True
        allow_create_albums_g = True

    @classmethod
    def get(cls, identifier):
        artist_data = cls._api.artist_infos(identifier)
        artist = artist_data['artist']
        artist['songs'] = artist_data['hotSongs'] or []
        artist = _deserialize(artist, NeteaseArtistSchema)
        return artist

    def create_songs_g(self):
        data = self._api.artist_songs(self.identifier, limit=0)
        count = int(data['total'])

        def g():
            offset = 0
            per = 50
            while offset < count:
                data = self._api.artist_songs(self.identifier, offset, per)
                for song_data in data['songs']:
                    yield _deserialize(song_data, V2SongSchema)
                # In reality, len(data['songs']) may smaller than per,
                # which is a bug of netease server side, so we set
                # offset to `offset + per` here.
                offset += per
                per = 100

        return SequentialReader(g(), count)

    def create_albums_g(self):
        data = self._api.artist_albums(self.identifier)
        if data['code'] != 200:
            yield from ()
        else:
            cur = 1
            while True:
                for album in data['hotAlbums']:
                    # the songs field will always be an empty list,
                    # we set it to None
                    album['songs'] = None
                    yield _deserialize(album, NeteaseAlbumSchema)
                    cur += 1
                if data['more']:
                    data = self._api.artist_albums(self.identifier, offset=cur)
                else:
                    break

    @property
    def desc(self):
        if self._desc is None:
            self._desc = self._api.artist_desc(self.identifier)
        return self._desc

    @desc.setter
    def desc(self, value):
        self._desc = value


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


class NPlaylistModel(PlaylistModel, NBaseModel):
    class Meta:
        fields = ('uid',)
        allow_create_songs_g = True

    def create_songs_g(self):
        data = self._api.playlist_detail_v3(self.identifier, limit=0)
        track_ids = data['trackIds']  # [{'id': 1, 'v': 1}, ...]
        count = len(track_ids)

        def g():
            offset = 0
            per = 50  # speed up first request
            while offset < count:
                end = min(offset + per, count)
                if end <= offset:
                    break
                ids = [track_id['id'] for track_id in track_ids[offset: end]]
                tracks_data = self._api.songs_detail_v3(ids)
                for track_data in tracks_data:
                    yield _deserialize(track_data, V2SongSchemaForV3)
                offset += per
                per = 800

        return SequentialReader(g(), count)

    @classmethod
    def get(cls, identifier):
        data = cls._api.playlist_detail_v3(identifier, limit=0)
        playlist = _deserialize(data, NeteasePlaylistSchema)
        return playlist

    def add(self, song_id, allow_exist=True):
        rv = self._api.op_music_to_playlist(song_id, self.identifier, 'add')
        if rv == 1:
            song = provider.song_get(song_id)
            self.songs.append(song)
            return True
        elif rv == -1:
            return True
        return False

    def remove(self, song_id, allow_not_exist=True):
        rv = self._api.op_music_to_playlist(song_id, self.identifier, 'del')
        if rv != 1:
            return False
        # XXX: make it O(1) if you want
        for song in self.songs:
            if song.identifier == song_id:
                self.songs.remove(song)
        return True


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
            playlist = _deserialize(playlist_data, NeteasePlaylistSchema)
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
        return create_g(self._api.user_favorite_artists, NeteaseArtistSchema)

    @fav_artists.setter
    def fav_artists(self, _): pass

    @property
    def fav_albums(self):
        return create_g(self._api.user_favorite_albums, NeteaseAlbumSchema)

    @fav_albums.setter
    def fav_albums(self, _): pass

    @cached_field()
    def cloud_songs(self):
        songs_data = self._api.cloud_songs()
        songs = []
        for song_data in songs_data:
            try:
                song = _deserialize(song_data['simpleSong'], V2SongSchemaForV3)
            except ValidationError:
                # FIXME: 有些云盘歌曲在 netease 上不存在，这时不能把它们转换成
                # SongModel。因为 SongModel 的逻辑没有考虑 song 不存在的情况。
                # 这类歌曲往往没有 ar/al 等字段，在反序列化的时候会报 ValidationError，
                # 所以这里如果检测到 ValidationError，就跳过这首歌曲。
                #
                # 可能的修复方法：
                # 1. 在 SongModel 上加一个 flag 来标识该歌曲是否为云盘歌曲，
                #    如果是的话，则使用 cloud_song_detail 接口来获取相关信息。
                name = song_data['simpleSong']['name']
                logger.warn(f'cloud song:{name} may not exist on netease, skip it.')
            else:
                songs.append(song)
        return songs

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
    V2MvSchema,
    NeteaseAlbumSchema,
    NeteaseArtistSchema,
    NeteasePlaylistSchema,
    NeteaseUserSchema,
    V2SongSchemaForV3, NDjradioSchema, NeteaseDjradioSchema,
)  # noqa
