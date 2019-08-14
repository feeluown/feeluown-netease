import logging

from marshmallow import Schema, post_load, fields
from fuocore.models import ModelExistence

logger = logging.getLogger(__name__)


class NeteaseMvSchema(Schema):
    identifier = fields.Int(requried=True, load_from='id')
    name = fields.Str(requried=True)
    cover = fields.Str(requried=True)
    brs = fields.Dict(requried=True)

    @post_load
    def create_model(self, data):
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


class NeteaseSongSchema(Schema):
    identifier = fields.Int(requried=True, load_from='id')
    mvid = fields.Int(requried=True)
    title = fields.Str(required=True, load_from='name')
    duration = fields.Float(required=True)
    url = fields.Str(allow_none=True)
    album = fields.Nested('NeteaseAlbumSchema')
    artists = fields.List(fields.Nested('NeteaseArtistSchema'))

    @post_load
    def create_model(self, data):
        album = data['album']
        artists = data['artists']

        # 在所有的接口中，song.album.songs 要么是一个空列表，
        # 要么是 null，这里统一置为 None。
        album.songs = None

        # 在有的接口中（比如歌单列表接口），album cover 的值是不对的，
        # 它会指向的是一个网易云默认的灰色图片，我们将其设置为 None，
        # artist cover 也有类似的问题。
        album.cover = None

        if artists:
            for artist in artists:
                artist.cover = None

        return NSongModel(**data)


class NSongSchemaV3(Schema):
    identifier = fields.Int(requried=True, load_from='id')
    mvid = fields.Int(requried=True, load_from='mv')
    title = fields.Str(required=True, load_from='name')
    duration = fields.Float(required=True, load_from='dt')
    url = fields.Str(allow_none=True)
    album = fields.Nested('NAlbumSchemaV3', load_from='al')
    artists = fields.List(fields.Nested('NArtistSchemaV3'), load_from='ar')

    @post_load
    def create_model(self, data):
        return NSongModel(**data)


class NeteaseAlbumSchema(Schema):
    identifier = fields.Int(required=True, load_from='id')
    name = fields.Str(required=True)
    cover = fields.Str(load_from='picUrl', allow_none=True)
    # 搜索接口返回的 album 数据中的 songs 为 None
    songs = fields.List(fields.Nested('NeteaseSongSchema'), allow_none=True)
    artists = fields.List(fields.Nested('NeteaseArtistSchema'))

    @post_load
    def create_model(self, data):
        return NAlbumModel(**data)


class NAlbumSchemaV3(Schema):
    # 如果 album 无效，id 则为 0
    # 只有当 album 无效时，name 才可能为 None
    identifier = fields.Int(required=True, load_from='id')
    name = fields.Str(required=True, allow_none=True)

    @post_load
    def create_model(self, data):
        album = NAlbumModel(**data)
        if album.identifier == 0:
            album.exists = ModelExistence.no
            album.name = ''
        return album


class NeteaseArtistSchema(Schema):
    identifier = fields.Int(required=True, load_from='id')
    name = fields.Str()
    cover = fields.Str(load_from='picUrl', allow_none=True)
    songs = fields.List(fields.Nested('NeteaseSongSchema'))

    @post_load
    def create_model(self, data):
        return NArtistModel(**data)


class NArtistSchemaV3(Schema):
    # 如果 artist 无效，id 则为 0
    # 只有当 artist 无效时，name 才可能为 None
    identifier = fields.Int(required=True, load_from='id')
    name = fields.Str(required=True, allow_none=True)

    @post_load
    def create_model(self, data):
        artist = NArtistModel(**data)
        if artist.identifier == 0:
            artist.exists = ModelExistence.no
            artist.name = ''
        return artist


class NeteasePlaylistSchema(Schema):
    identifier = fields.Int(required=True, load_from='id')
    uid = fields.Int(required=True, load_from='userId')
    name = fields.Str(required=True)
    desc = fields.Str(required=True, allow_none=True, load_from='description')
    cover = fields.Url(required=True, load_from='coverImgUrl')
    # songs field maybe null, though it can't be null in model
    songs = fields.List(fields.Nested(NeteaseSongSchema),
                        load_from='tracks',
                        allow_none=True)

    @post_load
    def create_model(self, data):
        if data.get('desc') is None:
            data['desc'] = ''
        return NPlaylistModel(**data)


class NeteaseUserSchema(Schema):
    identifier = fields.Int(required=True, load_from='id')
    name = fields.Str(required=True)
    playlists = fields.List(fields.Nested(NeteasePlaylistSchema))
    fav_playlists = fields.List(fields.Nested(NeteasePlaylistSchema))
    cookies = fields.Dict()

    @post_load
    def create_model(self, data):
        return NUserModel(**data)

class NeteaseSearchSchema(Schema):
    """搜索结果 Schema"""
    songs = fields.List(fields.Nested(NeteaseSongSchema))
    albums = fields.List(fields.Nested(NeteaseAlbumSchema))
    artists = fields.List(fields.Nested(NeteaseArtistSchema))
    playlists = fields.List(fields.Nested(NeteasePlaylistSchema), load_from='collects')

    @post_load
    def create_model(self, data):
        return NSearchModel(**data)
    


from .models import (
    NAlbumModel,
    NArtistModel,
    NPlaylistModel,
    NSongModel,
    NUserModel,
    NMvModel,
    NSearchModel
)
