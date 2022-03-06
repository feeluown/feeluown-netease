import json
from unittest.mock import patch
from unittest import TestCase

from fuo_netease.api import API
from fuo_netease.provider import provider


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


def test_():
    pass
