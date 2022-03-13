import json
import os

import pytest


def _read_json_fixture(path):
    path = os.path.join('data/fixtures', path)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


@pytest.fixture
def playlist_detail_v3__2829883282():
    return _read_json_fixture('playlist_detail_v3__2829883282.json')
