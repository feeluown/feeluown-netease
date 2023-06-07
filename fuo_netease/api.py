#!/usr/bin/env python
# encoding: UTF-8

import base64
import binascii
import hashlib
import os
import json
import logging

from bs4 import BeautifulSoup
import requests
from Crypto.Cipher import AES

from .excs import NeteaseIOError

site_uri = 'http://music.163.com'
uri = 'http://music.163.com/api'
uri_we = 'http://music.163.com/weapi'
uri_v1 = 'http://music.163.com/weapi/v1'
uri_v3 = 'http://music.163.com/weapi/v3'
uri_e = 'https://music.163.com/eapi'

logger = logging.getLogger(__name__)


class CodeShouldBe200(NeteaseIOError):
    def __init__(self, data):
        self._code = data['code']

    def __str__(self):
        return 'json code field should be 200, got {}'.format(self._code)


class API(object):
    def __init__(self):
        super().__init__()
        self.headers = {
            'Host': 'music.163.com',
            'Connection': 'keep-alive',
            'Referer': 'http://music.163.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/33.0.1750.152 Safari/537.36'
        }
        self._cookies = dict(appver="1.2.1", os="osx")
        self._http = None

    @property
    def cookies(self):
        return self._cookies

    def load_cookies(self, cookies):
        self._cookies.update(cookies)
        # 云盘资源发布仅有似乎不支持osx平台
        self._cookies.update(dict(appver="7.2.24", os="android"))

    def set_http(self, http):
        self._http = http

    @property
    def http(self):
        return requests if self._http is None else self._http

    def request(self, method, action, query=None, timeout=2):
        # logger.info('method=%s url=%s data=%s' % (method, action, query))
        if method == "GET":
            res = self.http.get(action, headers=self.headers,
                                cookies=self._cookies, timeout=timeout)
        elif method == "POST":
            res = self.http.post(action, data=query, headers=self.headers,
                                 cookies=self._cookies, timeout=timeout)
        elif method == "POST_UPDATE":
            res = self.http.post(action, data=query, headers=self.headers,
                                 cookies=self._cookies, timeout=timeout)
            self._cookies.update(res.cookies.get_dict())
        content = res.content
        content_str = content.decode('utf-8')
        content_dict = json.loads(content_str)
        return content_dict

    def login(self, country_code, username, pw_encrypt, phone=False):
        action = 'http://music.163.com/api/login/'
        phone_action = 'http://music.163.com/api/login/cellphone/'
        data = {
            'password': pw_encrypt,
            'rememberLogin': 'true'
        }
        if username.isdigit() and (len(username) == 11 or country_code):
            phone = True
            data.update({'phone': username, 'countrycode': country_code or '86'})
        else:
            data.update({'username': username})
        if phone:
            res_data = self.request("POST_UPDATE", phone_action, data)
            return res_data
        else:
            res_data = self.request("POST_UPDATE", action, data)
            return res_data

    def check_cookies(self):
        url = uri + '/push/init'
        data = self.request("POST_UPDATE", url, {})
        if data['code'] == 200:
            return True
        return False

    def confirm_captcha(self, captcha_id, text):
        action = uri + '/image/captcha/verify/hf?id=' + str(captcha_id) +\
            '&captcha=' + str(text)
        data = self.request('GET', action)
        return data

    def get_captcha_url(self, captcha_id):
        action = 'http://music.163.com/captcha?id=' + str(captcha_id)
        return action

    def user_profile(self, user_id):
        """
        {'nickname': 'cosven',
         'avatarImg': 'xx.jpg',
         'userType': 0,
         'authStatus': 0,
         'expertTags': None,
         'backgroundUrl': 'xx.jpg',
         'playCount': 2892,
         'createdplCnt': 8,
         'starPlaylist': {...},
         'playlist': [...],
         'code': 200
        }
        """
        action = uri_we + '/share/userprofile/info'
        data = {'userId': user_id}
        payload = self.encrypt_request(data)
        res_data = self.request('POST', action, payload)
        code = res_data['code']
        if code == 200:
            return res_data
        elif code == 400:
            logger.warn(f'user:{user_id} may be invalid')
        raise CodeShouldBe200(res_data)

    # 用户歌单
    def user_playlists(self, uid, offset=0, limit=200):
        action = uri + '/user/playlist/?offset=' + str(offset) +\
            '&limit=' + str(limit) + '&uid=' + str(uid)
        data = self.request('GET', action)
        if data['code'] == 200:
            return data['playlist']
        return []

    def user_favorite_albums(self, offset=0, limit=30):
        action = uri_we + '/album/sublist'
        data = {
            'offset': offset,
            'limit': limit,
            'csrf_token': self._cookies.get('__csrf')}
        payload = self.encrypt_request(data)
        res_data = self.request('POST', action, payload)
        if res_data['code'] == 200:
            return res_data
        return None

    def user_favorite_artists(self, offset=0, limit=30):
        action = uri_we + '/artist/sublist'
        data = {
            'offset': offset,
            'limit': limit,
            'csrf_token': self._cookies.get('__csrf')}
        payload = self.encrypt_request(data)
        res_data = self.request('POST', action, payload)
        if res_data['code'] == 200:
            return res_data
        return None

    # 搜索单曲(1)，歌手(100)，专辑(10)，歌单(1000)，用户(1002) *(type)*
    def search(self, s, stype=1, offset=0, total='true', limit=30):
        """get songs list from search keywords"""
        action = uri + '/search/get'
        data = {
            's': s,
            'type': stype,
            'offset': offset,
            'total': total,
            'limit': limit
        }
        resp = self.request('POST', action, data)
        if resp['code'] == 200:
            return resp['result']
        return []

    def playlist_detail_v3(self, pid, offset=0, limit=200):
        """
        该接口返回的 ['playlist']['trackIds'] 字段会包含所有的歌曲
        """
        action = '/playlist/detail'
        url = uri_v3 + action
        data = dict(id=pid, limit=limit, offset=offset, n=limit)
        payload = self.encrypt_request(data)
        res_data = self.request('POST', url, payload)
        if res_data['code'] == 200:
            return res_data['playlist']
        raise CodeShouldBe200(res_data)

    def update_playlist_name(self, pid, name):
        url = uri + '/playlist/update/name'
        data = {
            'id': pid,
            'name': name
        }
        res_data = self.request('POST', url, data)
        return res_data

    def new_playlist(self, uid, name='default'):
        url = uri + '/playlist/create'
        data = {
            'uid': uid,
            'name': name
        }
        res_data = self.request('POST', url, data)
        return res_data

    def delete_playlist(self, pid):
        url = uri + '/playlist/delete'
        data = {
            'id': pid,
            'pid': pid
        }
        return self.request('POST', url, data)

    def artist_infos(self, artist_id):
        """
        :param artist_id: artist_id
        :return: {
            code: int,
            artist: {artist},
            more: boolean,
            hotSongs: [songs]
        }
        """
        action = uri + '/artist/' + str(artist_id)
        data = self.request('GET', action)
        return data

    def artist_songs(self, artist_id, offset=0, limit=50):
        action = uri_we + '/artist/songs'
        data = dict(id=artist_id, limit=limit, offset=offset, n=limit)
        payload = self.encrypt_request(data)
        res_data = self.request('POST', action, payload)
        if res_data['code'] == 200:
            return res_data
        raise CodeShouldBe200(res_data)

    def artist_albums(self, artist_id, offset=0, limit=20):
        action = ('{uri}/artist/albums/{artist_id}?'
                  'offset={offset}&limit={limit}')
        action = action.format(uri=uri,
                               artist_id=artist_id,
                               offset=offset,
                               limit=limit)
        data = self.request('GET', action)
        return data

    # album id --> song id set
    def album_infos(self, album_id):
        """
        :param album_id:
        :return: {
            code: int,
            album: { album }
        }
        """
        action = uri + '/album/' + str(album_id)
        data = self.request('GET', action)
        if data['code'] == 200:
            return data['album']

    def album_desc(self, album_id):
        action = site_uri + '/album'
        data = {'id': album_id}
        res = self.http.get(action, data, headers=self.headers)
        if res is None:
            return None
        soup = BeautifulSoup(res.content, 'html.parser')
        albdescs = soup.select('.n-albdesc')
        if albdescs:
            return albdescs[0].prettify()
        return ''

    def artist_desc(self, artist_id):
        action = site_uri + '/artist/desc'
        data = {'id': artist_id}
        res = self.http.get(action, data, headers=self.headers)
        if res is None:
            return None
        soup = BeautifulSoup(res.content, 'html.parser')
        artdescs = soup.select('.n-artdesc')
        if artdescs:
            artdesc = artdescs[0]
            # FIXME: 艺术家描述是 html 格式的，它有一个 header 为
            # ``<h2>{artist_name}简介</h2>``, 而在 FeelUOwn 的 UI 设计中，
            # FeelUown 是把艺术家描述显示在艺术家名字下面，
            # 而艺术家名字也是用 ``<h2>{artist_name}</h2>`` 来渲染的，
            # 这样在视觉上就会出现两个非常相似的文字，非常难看，
            # 所以我们在这里把描述中的标题去掉。
            # 另外，我们还把描述中所有的 h2 header 替换成 h3 header。
            artdesc.h2.decompose()
            for h2 in artdesc.select('h2'):
                h2.name = 'h3'
            return artdesc.prettify()
        return ''

    # song id --> song url ( details )
    def song_detail(self, music_id):
        action = uri + '/song/detail/?id=' + str(music_id) + '&ids=[' +\
            str(music_id) + ']'
        data = self.request('GET', action)
        if data['songs']:
            return data['songs'][0]
        return

    def weapi_songs_url(self, music_ids, bitrate=320000):
        """
        When the expected bitrate song url does not exist, server will
        return a fallback song url. For example, we request a song
        url with bitrate=320000. If there only exists a song url with
        bitrate=128000, the server will return it.

        NOTE(cosven): After some manual testing, we found that the url is
        None in following cases:
        1. the song is for vip-user and the current user is not vip.
        2. the song is a paid song and the current user(may be a vip)
           has not bought it.
        """
        url = uri_we + '/song/enhance/player/url'
        data = {
            'ids': music_ids,
            'br': bitrate,
            'csrf_token': self._cookies.get('__csrf')
        }
        payload = self.encrypt_request(data)
        data = self.request('POST', url, payload)
        if data['code'] == 200:
            return data['data']
        return []

    def songs_detail(self, music_ids):
        """批量获取歌曲的详细信息（老版）

        经过测试 music_ids 不能超过 200 个。
        """
        music_ids = [str(music_id) for music_id in music_ids]
        action = uri + '/song/detail?ids=[' +\
            ','.join(music_ids) + ']'
        data = self.request('GET', action)
        if data['code'] == 200:
            return data['songs']
        return []

    def songs_detail_v3(self, music_ids):
        """批量获取歌曲的详细信息

        经过测试 music_ids 不能超过 1000 个
        """
        action = '/song/detail'
        url = uri_v3 + action
        params = {
            'c': json.dumps([{'id': id_} for id_ in music_ids]),
            'ids': json.dumps(music_ids)
        }
        payload = self.encrypt_request(params)
        data = self.request('POST', url, payload)
        if data['code'] == 200:
            return data['songs']
        return []

    def op_music_to_playlist(self, mid, pid, op):
        """
        :param op: add or del
        """
        url_add = uri + '/playlist/manipulate/tracks'
        trackIds = '["' + str(mid) + '"]'
        data_add = {
            'tracks': str(mid),  # music id
            'pid': str(pid),    # playlist id
            'trackIds': trackIds,  # music id str
            'op': op   # opation
        }
        data = self.request('POST', url_add, data_add)
        code = data.get('code')

        # 从歌单中成功的移除歌曲时，code 是 200
        # 当从歌单中移除一首不存在的歌曲时，code 也是 200
        # 当向歌单添加歌曲时，如果歌曲已经在列表当中，返回 code 为 502
        # code 为 521 时，可能是因为：绑定手机号后才可操作哦
        if code == 200:
            return 1
        elif code == 502:
            return -1
        else:
            return 0

    def set_music_favorite(self, mid, flag):
        url = uri + '/song/like'
        data = {
            "trackId": mid,
            "like": str(flag).lower(),
            "time": 0
        }
        return self.request("POST", url, data)

    def get_radio_music(self):
        url = uri + '/radio/get'
        data = self.request('GET', url)
        if data['code'] == 200:
            return data['data']
        return None

    def get_mv_detail(self, mvid):
        """Get mv detail
        :param mvid: mv id
        :return:
        """
        url = uri + '/mv/detail?id=' + str(mvid)
        data = self.request('GET', url)
        if data['code'] == 200:
            return data['data']
        raise CodeShouldBe200(data)

    def get_lyric_by_songid(self, mid):
        """Get song lyric
        :param mid: music id
        :return: {
            lrc: {
                version: int,
                lyric: str
            },
            tlyric: {
                version: int,
                lyric: str
            }
            sgc: bool,
            qfy: bool,
            sfy: bool,
            transUser: {},
            code: int,
        }
        """
        # tv 表示翻译。-1：表示要翻译，1：不要
        url = uri + '/song/lyric?' + 'id=' + str(mid) + '&lv=1&kv=1&tv=-1'
        return self.request('GET', url)

    def get_similar_song(self, mid, offset=0, limit=10):
        url = (f"http://music.163.com/api/discovery/simiSong"
               f"?songid={mid}&offset={offset}&total=true&limit={limit}")
        data = self.request('GET', url)
        if data['code'] == 200:
            return data['songs']
        raise CodeShouldBe200(data)

    def get_recommend_songs(self):
        url = uri_v3 + '/discovery/recommend/songs'
        payload = self.encrypt_request({})
        res_data = self.request('POST', url, payload)
        if res_data['code'] == 200:
            return res_data['data']['dailySongs']
        raise CodeShouldBe200(res_data)

    def get_recommend_playlists(self):
        url = uri + '/discovery/recommend/resource'
        payload = self.encrypt_request({})
        data = self.request('POST', url, payload)
        if data['code'] == 200:
            return data['recommend']
        raise CodeShouldBe200(data)

    def get_comment(self, comment_id):
        data = {
            'rid': comment_id,
            'offset': '0',
            'total': 'true',
            'limit': '20',
            'csrf_token': self._cookies.get('__csrf')
        }
        url = uri_v1 + '/resource/comments/' + comment_id
        payload = self.encrypt_request(data)
        res_data = self.request('POST', url, payload)
        if res_data['code'] == 200:
            return res_data
        raise CodeShouldBe200(res_data)

    def accumulate_pl_count(self, mid):
        data = {"ids": "[%d]" % mid, "br": 128000,
                "csrf_token": self._cookies.get('__scrf')}
        url = uri_we + '/pl/count'
        payload = self.encrypt_request(data)
        return self.request('POST', url, payload)

    def cloud_songs(self, offset=0, limit=30):
        data = dict(limit=limit, offset=offset)
        url = uri_v1 + '/cloud/get'
        payload = self.encrypt_request(data)
        res_data = self.request('POST', url, payload)
        if res_data['code'] == 200:
            return res_data
        raise CodeShouldBe200(res_data)

    def cloud_songs_detail(self, music_ids):
        data = dict(songIds=music_ids.split(","))
        url = uri_v1 + '/cloud/get/byids'
        payload = self.encrypt_request(data)
        return self.request('POST', url, payload)

    def cloud_songs_delete(self, music_ids):
        data = dict(songIds=music_ids.split(","))
        url = uri_we + '/cloud/del'
        payload = self.encrypt_request(data)
        return self.request('POST', url, payload)

    def cloud_song_match(self, sid, asid):
        url = uri + f'/cloud/user/song/match?songId={sid}&adjustSongId={asid}'
        data = self.request('GET', url)
        if data['code'] == 200:
            return data['data']
        raise CodeShouldBe200(data)

    def cloud_song_upload(self, path):
        def md5sum(file):
            md5sum = hashlib.md5()
            with open(file, 'rb') as f:
                # while chunk := f.read():
                #     md5sum.update(chunk)
                md5sum.update(f.read())
            return md5sum

        from .cloud_helpers.cloud_api import Cloud_API
        cloud_api = Cloud_API(self, uri_e)

        fname = os.path.basename(path)
        fext = path.split('.')[-1]
        '''Parsing file names'''
        fsize = os.stat(path).st_size
        md5 = md5sum(path).hexdigest()
        logger.debug(f'[-] Checking file ( MD5: {md5} )')
        cresult = cloud_api.GetCheckCloudUpload(md5)
        if cresult['code'] != 200:
            return 'UPLOAD_CHECK_FAILED'

        '''网盘资源发布 4 步走：'''
        '''1.拿到上传令牌 - 需要文件名，MD5，文件大小'''
        token = cloud_api.GetNosToken(fname, md5, fsize, fext)
        if token['code'] != 200:
            return 'TOKEN_ALLOC_FAILED'
        token = token['result']

        '''2. 若文件未曾上传完毕，则完成其上传'''
        if cresult['needUpload']:
            logger.info(f'[+] {fname} needs to be uploaded ( {fsize} B )')
            try:
                upload_result = cloud_api.SetUploadObject(
                    open(path, 'rb'),
                    md5, fsize, token['objectKey'], token['token']
                )
            except Exception:
                return 'UPLOAD_FAILED'
            logger.debug(f'[-] Response:\n  {upload_result}')

        '''3. 提交资源'''
        songId = cresult['songId']
        logger.debug(f'''[!] Assuming upload has finished,preparing to submit
        ID  :   {songId}
        MD5 :   {md5}
        NAME:   {fname}''')
        metadata = cloud_api.GetMetadata(path)
        submit_result = cloud_api.SetUploadCloudInfo(
            token['resourceId'], songId, md5, fname,
            song=metadata.get('title', '.'),
            artist=metadata.get('artist', '.'),
            album=metadata.get('album', '.')
        )
        if submit_result['code'] != 200:
            return 'SUBMIT_FAILED'
        logger.debug(f'[-] Response:\n  {submit_result}')

        '''4. 发布资源'''
        publish_result = cloud_api.SetPublishCloudResource(submit_result['songId'])
        if publish_result['code'] != 200:
            return 'PUBLISH_FAILED'
        logger.debug(f'[-] Response:\n  {publish_result}')

        return 'STATUS_SUCCEEDED'

    def subscribed_djradio(self, limit=0, offset=0):
        data = dict(limit=100, time=0, needFee=False)
        url = uri_e + '/djradio/subed/v1'
        payload = self.eapi_encrypt(b'/api/djradio/subed/v1', data)
        return self.request('POST', url, {'params': payload})

    def djradio_detail(self, radio_id):
        data = dict(id=radio_id)
        url = uri_e + '/djradio/v2/get'
        payload = self.eapi_encrypt(b'/api/djradio/v2/get', data)
        return self.request('POST', url, {'params': payload})

    def djradio_song_detail(self, id_):
        data = dict(id=id_)
        url = uri_e + '/dj/program/detail'
        payload = self.eapi_encrypt(b'/api/dj/program/detail', data)
        return self.request('POST', url, {'params': payload})

    def djradio_list(self, radio_id, limit=50, offset=0, asc=False):
        data = dict(radioId=radio_id, limit=limit, offset=offset, asc=asc)
        url = uri_e + '/v1/dj/program/byradio'
        payload = self.eapi_encrypt(b'/api/v1/dj/program/byradio', data)
        return self.request('POST', url, {'params': payload})

    def _create_aes_key(self, size):
        return (''.join([hex(b)[2:] for b in os.urandom(size)]))[0:16]

    def _aes_encrypt(self, text, key):
        pad = 16 - len(text) % 16
        text = text + pad * chr(pad)
        encryptor = AES.new(bytes(key, 'utf-8'), 2, b'0102030405060708')
        enc_text = encryptor.encrypt(bytes(text, 'utf-8'))
        enc_text_encode = base64.b64encode(enc_text)
        return enc_text_encode

    def _rsa_encrypt(self, text):
        e = '010001'
        n = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615'\
            'bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf'\
            '695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46'\
            'bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b'\
            '8e289dc6935b3ece0462db0a22b8e7'
        reverse_text = text[::-1]
        encrypted_text = pow(int(binascii.hexlify(reverse_text), 16),
                             int(e, 16), int(n, 16))
        return format(encrypted_text, "x").zfill(256)

    def eapi_encrypt(self, path, params):
        """
        eapi接口参数加密
        :param bytes path: 请求的路径
        :param params: 请求参数
        :return str: 加密结果
        """
        params = json.dumps(params, separators=(',', ':')).encode()
        sign_src = b'nobody' + path + b'use' + params + b'md5forencrypt'
        m = hashlib.md5()
        m.update(sign_src)
        sign = m.hexdigest()
        aes_src = path + b'-36cd479b6b5-' + params + b'-36cd479b6b5-' + sign.encode()
        pad = 16 - len(aes_src) % 16
        aes_src = aes_src + bytearray([pad] * pad)
        crypt = AES.new(b'e82ckenh8dichen8', AES.MODE_ECB)
        ret = crypt.encrypt(aes_src)
        return binascii.b2a_hex(ret).upper()

    def encrypt_request(self, data):
        text = json.dumps(data)
        first_aes_key = '0CoJUm6Qyw8W8jud'
        second_aes_key = self._create_aes_key(16)
        enc_text = self._aes_encrypt(
            self._aes_encrypt(text, first_aes_key).decode('ascii'),
            second_aes_key).decode('ascii')
        enc_aes_key = self._rsa_encrypt(second_aes_key.encode('ascii'))
        payload = {
            'params': enc_text,
            'encSecKey': enc_aes_key,
        }
        return payload


api = API()


if __name__ == '__main__':
    from fuo_netease.login_controller import LoginController
    user = LoginController.load()
    cookies, _ = user.cache_get('cookies')
    api.load_cookies(cookies)
    print(api.djradio_song_detail(1883706033))
