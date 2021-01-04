import logging

from feeluown.library import AbstractProvider, ProviderV2, ProviderFlags as PF, \
    CommentModel, BriefCommentModel, BriefUserModel
from feeluown.media import Quality
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
                                  name=user_data['nickname'],
                                  avatar_url=user_data['avatarUrl'])
            comment = CommentModel(identifier=comment_data['commentId'],
                                   source='netease',
                                   user=user,
                                   content=comment_data['content'],
                                   liked_count=comment_data['likedCount'],
                                   time=comment_data['time'] // 1000,
                                   parent=None,
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
        return self._song_get_q_media_mapping(song).get(quality)

    def _song_get_q_media_mapping(self, song):
        mapping, exists = song.cache_get('quality_media_mapping')
        if exists is True:
            return mapping
        songs = self.api.weapi_songs_url([int(song.identifier)], 999000)
        mapping = {}
        if songs and songs[0]['url']:
            # TODO: parse songs list and get more reasonable mapping
            mapping = {
                Quality.Audio.sq: songs[0]['url']
            }
        ttl = 60 * 20
        song.cache_set('quality_media_mapping', mapping, ttl)
        return mapping

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
