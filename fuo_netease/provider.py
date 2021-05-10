import logging

from feeluown.library import AbstractProvider, ProviderV2, ProviderFlags as PF, \
    CommentModel, BriefCommentModel, BriefUserModel, UserModel, \
    NoUserLoggedIn
from feeluown.media import Quality, Media
from feeluown.models import ModelType, SearchType
from .api import API


logger = logging.getLogger(__name__)


class NeteaseProvider(AbstractProvider, ProviderV2):
    class meta:
        identifier = 'netease'
        name = '网易云音乐'
        flags = {
            ModelType.song: (PF.model_v2 | PF.similar | PF.multi_quality |
                             PF.get | PF.hot_comments),
            ModelType.none: PF.current_user,
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
                         source='netease',
                         name=data['nickname'],
                         avatar_url=data['avatarImg'])
        return user

    def song_get(self, identifier):
        data = self.api.song_detail(int(identifier))
        return _deserialize(data, V2SongSchema)

    def song_list_similar(self, song):
        songs = self.api.get_similar_song(song.identifier)
        return [_deserialize(song, V2SongSchema) for song in songs]

    def song_list_quality(self, song):
        return list(self._song_get_q_media_mapping(song))

    def song_list_hot_comments(self, song):
        comment_thread_id = self._song_get_comment_thread_id(song)
        data = self.api.get_comment(comment_thread_id)
        hot_comments_data = data['hotComments']
        hot_comments = []
        for comment_data in hot_comments_data:
            user_data = comment_data['user']
            user = BriefUserModel(identifier=str(user_data['userId']),
                                  source='netease',
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
                                   source='netease',
                                   user=user,
                                   content=comment_data['content'],
                                   liked_count=comment_data['likedCount'],
                                   time=comment_data['time'] // 1000,
                                   parent=parent,
                                   root_comment_id=comment_data['parentCommentId'])
            hot_comments.append(comment)
        return hot_comments

    def _song_get_comment_thread_id(self, song):
        cache_key = 'comment_thread_id'
        comment_thread_id, exists = song.cache_get(cache_key)
        if exists is True:
            return comment_thread_id
        # FIXME: the following implicitly get comment_thread_id attribute
        upgraded_song = self.song_get(song.identifier)
        comment_thread_id, exists = upgraded_song.cache_get(cache_key)
        assert exists is True
        song.cache_set(cache_key, comment_thread_id)
        return comment_thread_id

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
            if highest_bitrate > 400000:
                q_media_mapping[Quality.Audio.shq] = (highest_bitrate,
                                                      song_url_data['url'],
                                                      song_url_data['type'])

            for key, quality in key_quality_mapping.items():
                if key in song_data:
                    # This resource is invalid for current user since the expected
                    # bitrate is large than the highest_bitrate
                    if (song_data[key]['br'] - highest_bitrate) > 10000:
                        continue
                    q_media_mapping[quality] = (song_data[key]['br'], None, None)

        ttl = 60 * 20
        song.cache_set('q_media_mapping', q_media_mapping, ttl)
        return q_media_mapping

    def search(self, keyword, type_, **kwargs):
        type_ = SearchType.parse(type_)
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


provider = NeteaseProvider()


from .models import _deserialize  # noqa
from .schemas import (  # noqa
    V2SongSchema,
    NeteaseSearchSchema,
)
