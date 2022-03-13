from unittest import mock

from fuo_netease import provider


def test_playlist_get(playlist_detail_v3__2829883282):
    mock_result = mock.patch.object(provider.api, 'playlist_detail_v3',
                                    return_value=playlist_detail_v3__2829883282)
    identifier = '2829883282'
    model = provider.playlist_get(identifier)
    assert model.identifier == identifier
