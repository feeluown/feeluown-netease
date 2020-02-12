import logging
import time

from fuocore.media import Quality, Media
from fuocore.models import cached_field
from fuocore.models import (
    BaseModel,
    SongModel,
    LyricModel,
    MvModel,
    PlaylistModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
    UserModel,
    SearchType
)
from fuocore.reader import RandomSequentialReader

from .provider import provider
from .excs import NeteaseIOError

logger = logging.getLogger(__name__)


def _deserialize(data, schema_cls):
    schema = schema_cls()
    obj = schema.load(data)
    return obj


def create_g(func, schema=None):
    data = func(limit=0)
    if data is None:
        raise NeteaseIOError('server responses with error status code')

    count = int(data['count'])

    def read_func(start, end):
        data = func(start, end - start)
        return [_deserialize(data, schema)
                for data in data['data']]

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


class NMvModel(MvModel, NBaseModel):
    class Meta:
        support_multi_quality = True
        fields = ['q_url_mapping']

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_mv_detail(identifier)
        if data is not None:
            mv = _deserialize(data['data'], NeteaseMvSchema)
            return mv
        return None

    def list_quality(self):
        return list(key for key, value in self.q_url_mapping.items()
                    if value is not None)

    def get_media(self, quality):
        if isinstance(quality, Quality.Video):  # Quality.Video Enum Item
            quality = quality.value
        return self.q_url_mapping.get(quality)


class NSongModel(SongModel):
    _api = provider.api

    class Meta:
        allow_get = True
        provider = provider
        fields = ['mvid', 'q_media_mapping', 'expired_at']
        fields_no_get = ['q_media_mapping', 'expired_at', 'url']
        support_multi_quality = True

    @classmethod
    def get(cls, identifier):
        data = cls._api.song_detail(int(identifier))
        song = _deserialize(data, NeteaseSongSchema)
        return song

    @classmethod
    def list(cls, identifiers):
        song_data_list = cls._api.songs_detail(identifiers)
        songs = []
        for song_data in song_data_list:
            song = _deserialize(song_data, NeteaseSongSchema)
            songs.append(song)
        return songs

    def _refresh_url(self):
        """刷新获取 url，失败的时候返回空而不是 None"""
        # FIXME: move q_media_mapping fetch logic to somewhere else
        songs = self._api.weapi_songs_url([int(self.identifier)], 999000)
        if songs and songs[0]['url']:
            self.url = songs[0]['url']
        else:
            self.url = ''
        self.q_media_mapping = {}
        if songs and songs[0]['url']:
            media = Media(songs[0]['url'], format=songs[0]['type'],
                          bitrate=songs[0]['br'] // 1000)
            if songs[0]['br'] > 320000:
                self.q_media_mapping = {'shq': media,
                                        'hq': None,
                                        'sq': None,
                                        'lq': None}
            if songs[0]['br'] == 320000:
                self.q_media_mapping = {'hq': media,
                                        'sq': None,
                                        'lq': None}
            if songs[0]['br'] == 192000:
                self.q_media_mapping = {'sq': media,
                                        'lq': None}
            if songs[0]['br'] == 128000:
                self.q_media_mapping = {'lq': media}
        self.expired_at = int(time.time()) + 60 * 20 * 1

    @property
    def is_expired(self):
        return self.expired_at is not None and time.time() >= self.expired_at

    # NOTE: if we want to override model attribute, we must
    # implement both getter and setter.
    @property
    def url(self):
        """
        We will always check if this song file exists in local library,
        if true, we return the url of the local file.

        .. note::

            As netease song url will be expired after a period of time,
            we can not use static url here. Currently, we assume that the
            expiration time is 20 minutes, after the url expires, it
            will be automaticly refreshed.
        """
        if not self._url:
            self._refresh_url()
        elif time.time() > self._expired_at:
            logger.info('song({}) url is expired, refresh...'.format(self))
            self._refresh_url()
        return self._url

    @url.setter
    def url(self, value):
        self._expired_at = time.time() + 60 * 20 * 1  # 20 minutes
        self._url = value

    @property
    def lyric(self):
        if self._lyric is not None:
            assert isinstance(self._lyric, LyricModel)
            return self._lyric
        data = self._api.get_lyric_by_songid(self.identifier)
        lrc = data.get('lrc', {})
        lyric = lrc.get('lyric', '')
        self._lyric = LyricModel(
            identifier=self.identifier,
            content=lyric
        )
        return self._lyric

    @lyric.setter
    def lyric(self, value):
        self._lyric = value

    @property
    def mv(self):
        if self._mv is not None:
            return self._mv
        # 这里可能会先获取一次 mvid
        if self.mvid is not None:
            mv = NMvModel.get(self.mvid)
            if mv is not None:
                self._mv = mv
                return self._mv
        self.mvid = None
        return None

    @mv.setter
    def mv(self, value):
        self._mv = value

    # multi quality support

    def list_quality(self):
        if self.q_media_mapping is None:
            self._refresh_url()
        return list(self.q_media_mapping.keys())

    def get_media(self, quality):
        if self.is_expired:
            self._refresh_url()
        media = self.q_media_mapping.get(quality)
        if media is None:
            q_bitrate_mapping = {
                'shq': 999000,
                'hq': 320000,
                'sq': 192000,
                'lq': 128000,
            }
            bitrate = q_bitrate_mapping[quality]
            songs = self._api.weapi_songs_url([int(self.identifier)], bitrate)
            if songs and songs[0]['url']:
                media = Media(songs[0]['url'],
                              format=songs[0]['type'],
                              bitrate=songs[0]['br'] // 1000)
                self.q_media_mapping[quality] = media
            else:
                self.q_media_mapping[quality] = ''
        return self.q_media_mapping.get(quality)


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
        allow_create_albums_g = True

    @classmethod
    def get(cls, identifier):
        artist_data = cls._api.artist_infos(identifier)
        artist = artist_data['artist']
        artist['songs'] = artist_data['hotSongs'] or []
        artist = _deserialize(artist, NeteaseArtistSchema)
        return artist

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


class NPlaylistModel(PlaylistModel, NBaseModel):
    class Meta:
        fields = ('uid',)
        allow_create_songs_g = True

    def create_songs_g(self):
        data = self._api.playlist_detail_v3(self.identifier, limit=0)
        if data is None:
            raise NeteaseIOError('server responses with error status code')

        track_ids = data['trackIds']  # [{'id': 1, 'v': 1}, ...]
        count = len(track_ids)

        def read_func(start, end):
            ids = [track_id['id'] for track_id in track_ids[start: end]]
            tracks_data = self._api.songs_detail_v3(ids)
            tracks = []
            for track_data in tracks_data:
                track = _deserialize(track_data, NSongSchemaV3)
                tracks.append(track)
            return tracks

        reader = RandomSequentialReader(count,
                                        read_func=read_func,
                                        max_per_read=200)
        return reader

    @classmethod
    def get(cls, identifier):
        data = cls._api.playlist_detail_v3(identifier, limit=0)
        playlist = _deserialize(data, NeteasePlaylistSchema)
        return playlist

    def add(self, song_id, allow_exist=True):
        rv = self._api.op_music_to_playlist(song_id, self.identifier, 'add')
        if rv == 1:
            song = NSongModel.get(song_id)
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
    def rec_songs(self):
        songs_data = self._api.get_recommend_songs()
        return [_deserialize(song_data, NeteaseSongSchema)
                for song_data in songs_data]

    def get_radio(self):
        songs_data = self._api.get_radio_music()
        if songs_data is None:
            logger.error('data should not be None')
            return None
        return [_deserialize(song_data, NeteaseSongSchema)
                for song_data in songs_data]


def search(keyword, **kwargs):
    type_ = SearchType.parse(kwargs['type_'])
    type_type_map = {
        SearchType.so: 1,
        SearchType.al: 10,
        SearchType.ar: 100,
        SearchType.pl: 1000,
    }
    data = provider.api.search(keyword, stype=type_type_map[type_])
    result = _deserialize(data, NeteaseSearchSchema)
    result.q = keyword
    return result


# import loop
from .schemas import (
    NeteaseSongSchema,
    NeteaseMvSchema,
    NeteaseAlbumSchema,
    NeteaseArtistSchema,
    NeteasePlaylistSchema,
    NeteaseUserSchema,
    NSongSchemaV3,
    NeteaseSearchSchema
)  # noqa
