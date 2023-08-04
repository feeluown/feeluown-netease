import logging

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


def create_cloud_songs_g(func, func_private, schema=None, schema_private=None,
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
        private_songs_info = []
        for idx, song_data in enumerate(songs_data[data_field]):
            if data_key:
                song_data = song_data[data_key]
            if song_data['id'] == song_data['s_id']:
                # FIXME: 有些云盘歌曲在 netease 上不存在，这时不能把它们转换成
                # SongModel。因为 SongModel 的逻辑没有考虑 song 不存在的情况。
                name = song_data['name']
                logger.warning(f'cloud song:{name} may not exist on netease.')
                private_songs_info.append((idx, song_data['id']))
            else:
                song = _deserialize(song_data, schema)
                songs.append(song)

        if private_songs_info:
            private_song_ids = ','.join([str(id) for (_, id) in private_songs_info])
            private_songs_data = func_private(private_song_ids)
            for idx, song_data in enumerate(private_songs_data[data_field]):
                song = _deserialize(song_data, schema_private)
                songs.insert(private_songs_info[idx][0], song)

        return songs

    reader = RandomSequentialReader(count,
                                    read_func=read_func,
                                    max_per_read=200)
    return reader
