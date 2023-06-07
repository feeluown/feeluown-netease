import logging

from feeluown.library import AbstractProvider, ProviderV2, ProviderFlags as PF, \
    CommentModel, BriefCommentModel, BriefUserModel, UserModel, \
    NoUserLoggedIn, LyricModel, ModelNotFound
from feeluown.media import Quality, Media
from feeluown.library import ModelType, SearchType
from feeluown.utils.cache import cached_field
from feeluown.utils.reader import create_reader, SequentialReader
from .api import API


logger = logging.getLogger(__name__)
SOURCE = 'netease'


class NeteaseProvider(AbstractProvider, ProviderV2):
    class meta:
        identifier = SOURCE
        name = '网易云音乐'
        # TODO: remove
        flags = {
            ModelType.song: (PF.model_v2 | PF.similar | PF.multi_quality |
                             PF.get | PF.hot_comments | PF.web_url |
                             PF.lyric | PF.mv),
            ModelType.album: (PF.model_v2 | PF.get),
            ModelType.artist: (PF.model_v2 | PF.get | PF.songs_rd | PF.albums_rd),
            ModelType.video: (PF.model_v2 | PF.get | PF.multi_quality),
            ModelType.playlist: (PF.model_v2 | PF.get |
                                 PF.songs_rd | PF.add_song | PF.remove_song),
            ModelType.none: PF.current_user,
        }

    def __init__(self):
        super().__init__()
        self.api = API()

    @property
    def identifier(self):
        return SOURCE

    @property
    def name(self):
        return '网易云音乐'

    def auth(self, user):
        cookies, exists = user.cache_get('cookies')
        assert exists and cookies is not None
        self._user = user
        self.api.load_cookies(cookies)

    def has_current_user(self):
        return self._user is not None

    def get_current_user(self):
        if self._user is None:
            raise NoUserLoggedIn
        user = self.user_get(self._user.identifier)
        return user

    def user_get(self, identifier):
        data = self.api.user_profile(identifier)
        user = UserModel(identifier=str(identifier),
                         source=SOURCE,
                         name=data['nickname'],
                         avatar_url=data['avatarImg'])
        return user

    def current_user_fav_djradios(self):
        return create_g(self.api.subscribed_djradio, NeteaseDjradioSchema, 'djRadios')

    def current_user_fav_artists(self):
        return create_g(self.api.user_favorite_artists, V2BriefArtistSchema)

    def current_user_fav_albums(self):
        return create_g(self.api.user_favorite_albums, V2BriefAlbumSchema)

    def current_user_cloud_songs(self):
        return create_cloud_songs_g(
            self.api.cloud_songs,
            self.api.cloud_songs_detail,
            V2SongSchemaForV3,
            NCloudSchema,
            data_key='simpleSong'
        )

    def current_user_playlists(self):
        user_id = str(self._user.identifier)
        data_playlists = self.api.user_playlists(user_id)
        playlists = []
        fav_playlists = []
        for pl in data_playlists:
            if str(pl['userId']) == user_id:
                playlists.append(pl)
            else:
                fav_playlists.append(pl)
        return [_deserialize(e, V2PlaylistSchema) for e in playlists], \
            [_deserialize(e, V2PlaylistSchema) for e in fav_playlists]

    def current_user_get_radio_songs(self):
        songs_data = self.api.get_radio_music()
        if songs_data is None:
            logger.error('data should not be None')
            return None
        return [_deserialize(song_data, V2SongSchema)
                for song_data in songs_data]

    @cached_field()
    def current_user_rec_playlists_p(self):
        playlists_data = self.api.get_recommend_playlists()
        rec_playlists = []
        for playlist_data in playlists_data:
            # FIXME: GUI模式下无法显示歌单描述
            playlist_data['coverImgUrl'] = playlist_data['picUrl']
            playlist_data['description'] = None
            playlist = _deserialize(playlist_data, V2PlaylistSchema)
            rec_playlists.append(playlist)
        return rec_playlists

    # 根据过去经验，每日推荐歌曲在每天早上 6:00 刷新，
    # ttl 设置为 60s 是为了能够比较即时的获取今天推荐。
    @cached_field(ttl=60)
    def current_user_rec_songs_p(self):
        songs_data = self.api.get_recommend_songs()
        return [_deserialize(song_data, V2SongSchemaForV3)
                for song_data in songs_data]

    def song_get(self, identifier):
        data = self.api.song_detail(int(identifier))
        return _deserialize(data, V2SongSchema)

    def song_list_similar(self, song):
        songs = self.api.get_similar_song(song.identifier)
        return [_deserialize(song, V2SongSchema) for song in songs]

    def song_get_lyric(self, song):
        data = self.api.get_lyric_by_songid(song.identifier)
        return LyricModel(
            source=SOURCE,
            identifier=self.identifier,
            content=data.get('lrc', {}).get('lyric', ''),
            trans_content=data.get('tlyric', {}).get('lyric', ''),
        )

    def song_get_mv(self, song):
        cache_key = 'mv_id'
        mvid, exists = song.cache_get(cache_key)
        if exists is not True:
            # FIXME: the following implicitly get mv_id attribute
            upgraded_song = self.song_get(song.identifier)
            mvid, exists = upgraded_song.cache_get(cache_key)
            assert exists is True
            song.cache_set(cache_key, mvid)

        if mvid:  # if mvid is valid
            data = self.api.get_mv_detail(mvid)
            mv = _deserialize(data, V2MvSchema)
            return mv
        return None

    def upload_song(self, path: str) -> bool:
        return self.api.cloud_song_upload(path) == 'STATUS_SUCCEEDED'

    def song_list_quality(self, song):
        return list(self._song_get_q_media_mapping(song))

    def song_list_hot_comments(self, song):
        comment_thread_id = self._model_cache_get_or_fetch(song, 'comment_thread_id')
        data = self.api.get_comment(comment_thread_id)
        hot_comments_data = data['hotComments']
        hot_comments = []
        for comment_data in hot_comments_data:
            user_data = comment_data['user']
            user = BriefUserModel(identifier=str(user_data['userId']),
                                  source=SOURCE,
                                  name=user_data['nickname'])
            be_replied = comment_data['beReplied']
            if be_replied:
                replied_comment_data = be_replied[0]
                parent = BriefCommentModel(
                    identifier=replied_comment_data['beRepliedCommentId'],
                    user_name=replied_comment_data['user']['nickname'],
                    content=replied_comment_data['content']
                )
            else:
                parent = None
            comment = CommentModel(identifier=comment_data['commentId'],
                                   source=SOURCE,
                                   user=user,
                                   content=comment_data['content'],
                                   liked_count=comment_data['likedCount'],
                                   time=comment_data['time'] // 1000,
                                   parent=parent,
                                   root_comment_id=comment_data['parentCommentId'])
            hot_comments.append(comment)
        return hot_comments

    def song_get_media(self, song, quality):
        q_media_mapping = self._song_get_q_media_mapping(song)
        if quality not in q_media_mapping:
            return None
        song_id = int(song.identifier)
        bitrate, url, format = q_media_mapping.get(quality)
        # None means the url is not fetched, so try to fetch it.
        if url is None:
            songs_data = self.api.weapi_songs_url([song_id], bitrate)
            if songs_data:
                song_data = songs_data[0]
                url = song_data['url']
                actual_bitrate = song_data['br']
                format = song_data['type']
                # Check the url bitrate while it is not empty. Api
                # may return a fallback bitrate when the expected bitrate
                # resource is not valid.
                if url and abs(actual_bitrate - bitrate) >= 10000:
                    logger.warning(
                        f'The actual bitrate is {actual_bitrate} '
                        f'while we want {bitrate}. '
                        f'[song:{song_id}].'
                    )
        if url:
            media = Media(url, bitrate=bitrate//1000, format=format)
            # update value in cache
            q_media_mapping[quality] = (bitrate, url, format)
            return media
        logger.error('This should not happend')
        return None

    def _song_get_q_media_mapping(self, song):
        q_media_mapping, exists = song.cache_get('q_media_mapping')
        if exists is True:
            return q_media_mapping

        song_id = int(song.identifier)
        songs_data = self.api.songs_detail_v3([song_id])
        if songs_data:
            q_media_mapping = {}  # {Quality.Audio: (bitrate, url, format)}
            song_data = songs_data[0]
            key_quality_mapping = {
                'h': Quality.Audio.hq,
                'm': Quality.Audio.sq,
                'l': Quality.Audio.lq,
            }

            # Trick: try to find the highest quality url
            # When the song is only for vip/paid user and current user is non-vip,
            # the highest bitrate is 0, which means this song is unavailable
            # for current user.
            songs_url_data = self.api.weapi_songs_url([song_id], 999000)
            assert songs_url_data, 'length should not be 0'
            song_url_data = songs_url_data[0]
            highest_bitrate = song_url_data['br']
            # When the bitrate is large than 320000, the quality is treated as
            # lossless. We set the threshold to 400000 here.
            # Note(cosven): From manual testing, the bitrate of lossless media
            # can be 740kbps, 883kbps, 1411kbps, 1777kbps.
            if song_url_data['url'] and 'privatecloud' in song_url_data['url']:
                # 对于云盘歌曲, netease会抛弃官方音乐地址, 只会返回自己上传的音乐链接
                # bitrate不由用户提供 由官方估算， 且不再是标准的320, 192, 128
                q_media_mapping[Quality.Audio.shq] = (highest_bitrate,
                                                      song_url_data['url'],
                                                      song_url_data['type'])
            else:
                if highest_bitrate > 400000:
                    q_media_mapping[Quality.Audio.shq] = (highest_bitrate,
                                                          song_url_data['url'],
                                                          song_url_data['type'])

                for key, quality in key_quality_mapping.items():
                    # Ensure the quality info exists.
                    if key in song_data and song_data[key] is not None:
                        # This resource is invalid for current user since the expected
                        # bitrate is large than the highest_bitrate
                        if (song_data[key]['br'] - highest_bitrate) > 10000:
                            continue
                        q_media_mapping[quality] = (song_data[key]['br'], None, None)

        ttl = 60 * 20
        song.cache_set('q_media_mapping', q_media_mapping, ttl)
        return q_media_mapping

    def song_get_web_url(self, song):
        return f'https://music.163.com/#/song?id={song.identifier}'

    def video_get(self, identifier):
        prefix, real_id = identifier.split('_')
        assert prefix == 'mv'
        data = self.api.get_mv_detail(real_id)
        mv = _deserialize(data, V2MvSchema)
        return mv

    def video_get_media(self, video, quality):
        q_media_mapping = self._model_cache_get_or_fetch(video, 'q_media_mapping')
        return q_media_mapping.get(quality)

    def video_list_quality(self, video):
        q_media_mapping = self._model_cache_get_or_fetch(video, 'q_media_mapping')
        return list(q_media_mapping.keys())

    def album_get(self, identifier):
        album_data = self.api.album_infos(identifier)
        if album_data is None:
            raise ModelNotFound
        description = self.api.album_desc(identifier)
        album_data['description'] = description
        album = _deserialize(album_data, V2AlbumSchema)
        return album

    def album_create_songs_rd(self, album):
        album_with_songs = self.album_get(album.identifier)
        return create_reader(album_with_songs.songs)

    def artist_get(self, identifier):
        artist_data = self.api.artist_infos(identifier)
        artist = artist_data['artist']
        artist['songs'] = artist_data['hotSongs'] or []
        description = self.api.artist_desc(identifier)
        artist['description'] = description
        artist['aliases'] = []
        model = _deserialize(artist, V2ArtistSchema)
        return model

    # TODO: artist create albums g
    # TODO: artist create songs g
    def artist_create_songs_rd(self, artist):
        data = self.api.artist_songs(artist.identifier, limit=0)
        count = int(data['total'])

        def g():
            offset = 0
            per = 50
            while offset < count:
                data = self.api.artist_songs(artist.identifier, offset, per)
                for song_data in data['songs']:
                    yield _deserialize(song_data, V2SongSchema)
                    # In reality, len(data['songs']) may smaller than per,
                    # which is a bug of netease server side, so we set
                    # offset to `offset + per` here.
                offset += per
                per = 100

        return SequentialReader(g(), count)

    def artist_create_albums_rd(self, artist):

        def g():
            data = self.api.artist_albums(artist.identifier)
            if data['code'] != 200:
                yield from ()
            else:
                cur = 1
                while True:
                    for album in data['hotAlbums']:
                        # the songs field will always be an empty list,
                        # we set it to None
                        album['songs'] = None
                        yield _deserialize(album, V2AlbumSchema)
                        cur += 1
                    if data['more']:
                        data = self.api.artist_albums(artist.identifier, offset=cur)
                    else:
                        break

        return create_reader(g())

    def playlist_get(self, identifier):
        data = self.api.playlist_detail_v3(identifier, limit=0)
        playlist = _deserialize(data, V2PlaylistSchema)
        return playlist

    def djradio_create_songs_rd(self, djradio_id):
        data = self.api.djradio_list(djradio_id, limit=1, offset=0)
        count = data.get('count', 0)

        def g():
            offset = 0
            per = 50  # speed up first request
            while offset < count:
                tracks_data = self.api.djradio_list(
                    djradio_id, limit=per, offset=offset)
                for track_data in tracks_data.get('programs', []):
                    yield _deserialize(track_data, NDjradioSchema)
                offset += per
        return create_reader(g())

    def playlist_create_songs_rd(self, playlist):
        if playlist.identifier.startswith(DjradioPrefix):
            return self.djradio_create_songs_rd(playlist.identifier[len(DjradioPrefix):])

        data = self.api.playlist_detail_v3(playlist.identifier, limit=0)
        track_ids = data['trackIds']  # [{'id': 1, 'v': 1}, ...]
        count = len(track_ids)

        def g():
            offset = 0
            # 第一次请求应该尽可能快一点，所以这里只获取少量的歌曲。
            # 综合页面展示以及请求速度，拍脑袋将值设置为 50。
            per = 50
            while offset < count:
                end = min(offset + per, count)
                if end <= offset:
                    break
                ids = [track_id['id'] for track_id in track_ids[offset: end]]
                # NOTE(cosven): 记忆中这里有个坑，传入的 id 个数和返回的歌曲个数
                # 不一定相等。比如在一个叫做“万首歌单”的歌单里面，有的歌曲是
                # 获取不到信息的。这也是这里为什么用 SequentialReader 而不是
                # RandomSequentialReader 的原因。
                tracks_data = self.api.songs_detail_v3(ids)
                for track_data in tracks_data:
                    yield _deserialize(track_data, V2SongSchemaForV3)
                offset += per
                # 这里设置为 800 主要是为 readall 的场景考虑的。假设这个值设置很小，
                # 那当这个歌单歌曲数量比较多的时候（比如一万首），需要很多个请求
                # 才能获取到全部的歌曲。
                per = 800

        return SequentialReader(g(), count)

    def playlist_remove_song(self, playlist, song):
        song_id = song.identifier
        rv = self.api.op_music_to_playlist(song_id, playlist.identifier, 'del')
        if rv != 1:
            return False
        return True

    def playlist_add_song(self, playlist, song):
        song_id = song.identifier
        rv = self.api.op_music_to_playlist(song_id, playlist.identifier, 'add')
        if rv == 1:
            song = provider.song_get(song_id)
            return True
        elif rv == -1:
            return True
        return False

    def search(self, keyword, type_, **kwargs):
        type_ = SearchType.parse(type_)
        type_type_map = {
            SearchType.so: 1,
            SearchType.al: 10,
            SearchType.ar: 100,
            SearchType.pl: 1000,
        }
        data = provider.api.search(keyword, stype=type_type_map[type_])
        data['q'] = keyword
        result = _deserialize(data, NeteaseSearchSchema)
        return result


provider = NeteaseProvider()


from .models import _deserialize, create_g, create_cloud_songs_g  # noqa
from .schemas import (  # noqa
    V2SongSchema,
    V2SongSchemaForV3,
    V2MvSchema,
    V2AlbumSchema,
    V2ArtistSchema,
    V2BriefArtistSchema,
    V2BriefAlbumSchema,
    V2PlaylistSchema,
    NeteaseDjradioSchema,
    NeteaseSearchSchema,
    NDjradioSchema,
    NCloudSchema,
    DjradioPrefix,
)
