import json
from unittest.mock import patch
from unittest import TestCase

from fuo_netease.api import API
from fuo_netease.provider import provider
from fuo_netease.models import NSongModel


with open('data/fixtures/song.json') as f:
    data_song = json.load(f)['songs'][0]

with open('data/fixtures/media.json') as f:
    data_media = json.load(f)

with open('data/fixtures/album.json') as f:
    data_album = json.load(f)['album']

with open('data/fixtures/artist.json') as f:
    data_artist = json.load(f)

with open('data/fixtures/playlist.json') as f:
    data_playlist = json.load(f)

with open('data/fixtures/search.json') as f:
    data_search = json.load(f)


class TestNeteaseModel(TestCase):
    def setUp(self):
        self.song = NSongModel(identifier=1,
                               title='dummy',
                               url=None,)

    @patch.object(API, 'songs_detail', return_value=[data_song])
    @patch.object(API, 'song_detail', return_value=data_song)
    def test_song_model(self, mock_song_detail, mock_songs_detail):
        song = provider.Song.get(-1)
        self.assertEqual(song.identifier, 29019227)
        songs = provider.Song.list([-1])
        self.assertEqual(songs[0].identifier, 29019227)

    @patch.object(API, 'get_lyric_by_songid', return_value={})
    @patch.object(API, 'song_detail', return_value=data_song)
    def test_song_lyric(self, mock_song_detail, mock_song_lyric):
        song = provider.Song.get(-1)
        self.assertEqual(song.lyric.content, '')
        self.assertTrue(mock_song_lyric.called)

    @patch.object(API, 'album_desc', return_value='desc')
    @patch.object(API, 'album_infos', return_value=data_album)
    def test_album_model(self, mock_album_detail, mock_album_desc):
        album = provider.Album.get(-1)
        self.assertEqual(album.identifier, 2980029)
        self.assertEqual(album.desc, 'desc')
        self.assertTrue(mock_album_desc.called)
