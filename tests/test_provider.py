from unittest import mock

from fuo_netease import provider


def test_playlist_get(playlist_detail_v3__2829883282):
    mock.patch.object(provider.api, 'playlist_detail_v3',
                      return_value=playlist_detail_v3__2829883282)
    identifier = '2829883282'
    model = provider.playlist_get(identifier)
    assert model.identifier == identifier


def test_playlist_create_songs_rd(songs_detail_v3__191232):
    total_count = 8050
    with mock.patch.object(provider.api, 'playlist_detail_v3',
                           return_value={'trackIds': [{'id': 1}]*total_count}):
        with mock.patch.object(provider.api, 'songs_detail_v3',
                               return_value=songs_detail_v3__191232) as mock_song_detail:
            playlist = mock.Mock()
            playlist.identifier = '111'
            provider.playlist_create_songs_rd(playlist).readall()
            # 这个调用次数和实现强相关。
            assert mock_song_detail.call_count == 11  # 8050 = per(50)*1 + per(800)*10
