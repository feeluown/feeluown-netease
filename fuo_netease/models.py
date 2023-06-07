import logging

from marshmallow.exceptions import ValidationError
from feeluown.utils.reader import RandomSequentialReader

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
