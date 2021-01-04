import logging

from marshmallow import Schema, post_load, fields, EXCLUDE

from feeluown.library import (
    SongModel, BriefAlbumModel, BriefArtistModel,
)
from feeluown.models import ModelExistence

logger = logging.getLogger(__name__)


class BaseSchema(Schema):
    source = fields.Str(missing='netease')

    class Meta:
        unknown = EXCLUDE


Schema = BaseSchema


def create_model(model_cls, data, fields_to_cache=None):
    """
    maybe this function should be provided by feeluown

    :param fields_to_cache: list of fields name to be cached
    """
    if fields_to_cache is not None:
        cache_data = {}
        for field in fields_to_cache:
            value = data.pop(field)
            if value is not None:
                cache_data[field] = value
        model = model_cls(**data)
        for field, value in cache_data.items():
            model.cache_set(field, value)
    else:
        model = model_cls(**data)
    return model


class NeteaseMvSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str(required=True)
    cover = fields.Str(required=True)
    brs = fields.Dict(required=True)

    @post_load
    def create_model(self, data, **kwargs):
        brs = data['brs']
        fhd = hd = sd = ld = None
        for q, url in brs.items():
            if q == '1080':
                fhd = url
            elif q == '720':
                hd = url
            elif q == '480':
                sd = url
            elif q == '240':
                ld = url
            else:
                logger.warning('There exists another quality:%s mv.', q)
        data['q_url_mapping'] = dict(fhd=fhd, hd=hd, sd=sd, ld=ld)
        return NMvModel(**data)


class V2BriefAlbumSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str(required=True)
    # cover = fields.Str(data_key='picUrl', allow_none=True)
    artist = fields.Dict()

    @post_load
    def create_v2_model(self, data, **kwargs):
        artist = data.pop('artist')
        data['artists_name'] = artist['name']
        return BriefAlbumModel(**data)


class V2BriefArtistSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str()
    # cover = fields.Str(data_key='picUrl', allow_none=True)
    # songs = fields.List(fields.Nested('V2SongSchema'))

    @post_load
    def create_v2_model(self, data, **kwargs):
        return BriefArtistModel(**data)


class V2SongSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    title = fields.Str(required=True, data_key='name')
    duration = fields.Float(required=True)
    album = fields.Nested('V2BriefAlbumSchema')
    artists = fields.List(fields.Nested('V2BriefArtistSchema'))

    mv_id = fields.Int(required=True, data_key='mvid')
    comment_thread_id = fields.Str(data_key='commentThreadId',
                                   allow_none=True, missing=None)

    @post_load
    def create_v2_model(self, data, **kwargs):
        return create_model(SongModel, data, ['mv_id', 'comment_thread_id'])


class NSongSchemaV3(Schema):
    identifier = fields.Int(required=True, data_key='id')
    mvid = fields.Int(required=True, data_key='mv')
    title = fields.Str(required=True, data_key='name')
    duration = fields.Float(required=True, data_key='dt')
    url = fields.Str(allow_none=True)
    album = fields.Nested('NAlbumSchemaV3', data_key='al')
    artists = fields.List(fields.Nested('NArtistSchemaV3'), data_key='ar')

    @post_load
    def create_model(self, data, **kwargs):
        return NSongModel(**data)


class NeteaseAlbumSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str(required=True)
    cover = fields.Str(data_key='picUrl', allow_none=True)
    # 收藏和搜索接口返回的 album 数据中的 songs 为 None
    songs = fields.List(fields.Nested('V2SongSchema'), allow_none=True)
    artists = fields.List(fields.Nested('NeteaseArtistSchema'))

    @post_load
    def create_model(self, data, **kwargs):
        return NAlbumModel(**data)


class NAlbumSchemaV3(Schema):
    # 如果 album 无效，id 则为 0
    # 只有当 album 无效时，name 才可能为 None
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str(required=True, allow_none=True)

    @post_load
    def create_model(self, data, **kwargs):
        album = NAlbumModel(**data)
        if album.identifier == 0:
            album.exists = ModelExistence.no
            album.name = ''
        return album


class NeteaseArtistSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str()
    cover = fields.Str(data_key='picUrl', allow_none=True)
    songs = fields.List(fields.Nested('V2SongSchema'))

    @post_load
    def create_model(self, data, **kwargs):
        return NArtistModel(**data)


class NArtistSchemaV3(Schema):
    # 如果 artist 无效，id 则为 0
    # 只有当 artist 无效时，name 才可能为 None
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str(required=True, allow_none=True)

    @post_load
    def create_model(self, data, **kwargs):
        artist = NArtistModel(**data)
        if artist.identifier == 0:
            artist.exists = ModelExistence.no
            artist.name = ''
        return artist


class NeteasePlaylistSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    uid = fields.Int(required=True, data_key='userId')
    name = fields.Str(required=True)
    desc = fields.Str(required=True, allow_none=True, data_key='description')
    cover = fields.Url(required=True, data_key='coverImgUrl')
    # songs field maybe null, though it can't be null in model
    songs = fields.List(fields.Nested(V2SongSchema),
                        data_key='tracks',
                        allow_none=True)

    @post_load
    def create_model(self, data, **kwargs):
        if data.get('desc') is None:
            data['desc'] = ''
        return NPlaylistModel(**data)


class NeteaseUserSchema(Schema):
    identifier = fields.Int(required=True, data_key='id')
    name = fields.Str(required=True)
    playlists = fields.List(fields.Nested(NeteasePlaylistSchema))
    fav_playlists = fields.List(fields.Nested(NeteasePlaylistSchema))
    cookies = fields.Dict()

    @post_load
    def create_model(self, data, **kwargs):
        return NUserModel(**data)


class NeteaseSearchSchema(Schema):
    """搜索结果 Schema"""
    songs = fields.List(fields.Nested(V2SongSchema))
    albums = fields.List(fields.Nested(NeteaseAlbumSchema))
    artists = fields.List(fields.Nested(NeteaseArtistSchema))
    playlists = fields.List(fields.Nested(NeteasePlaylistSchema))

    @post_load
    def create_model(self, data, **kwargs):
        return NSearchModel(**data)


from .models import (  # noqa
    NAlbumModel,
    NArtistModel,
    NPlaylistModel,
    NSongModel,
    NUserModel,
    NMvModel,
    NSearchModel
)  # noqa
