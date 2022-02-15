import requests
import json

from . import security
BUCKET = 'jd-musicrep-privatecloud-audio-public'


def GenerateCheckToken():
    '''Generates `checkToken` parameter ,which is needed by a handful of Weapis'''
    return security.wm_generate_config_chiper_bc(security.wm_generate_OTP_b())


class Cloud_API:
    def __init__(self, api, uri_e):
        self.api = api
        self.uri_e = uri_e

    def GetCheckCloudUpload(self, md5, ext='', length=0, bitrate=0, songId=0, version=1, cookies=None):
        '''移动端 - 检查云盘资源

        Args:
            md5 (str): 资源MD5哈希
            ext (str, optional): 文件拓展名. Defaults to ''.
            length (int, optional): 文件大小. Defaults to 0.
            bitrate (int, optional): 音频 - 比特率. Defaults to 0.
            songId (int, optional): 云盘资源ID. Defaults to 0 表示新资源.
            version (int, optional): 上传版本. Defaults to 1.

        Returns:
            dict
        '''
        data = {"songId": str(songId), "version": str(version), "md5": str(md5),
                "length": str(length), "ext": str(ext), "bitrate": str(bitrate),
                "checkToken": GenerateCheckToken()}
        url = self.uri_e + '/cloud/upload/check'
        payload = self.api.eapi_encrypt(b'/api/cloud/upload/check', data)
        return self.api.request('POST', url, {'params': payload})

    def GetNosToken(self, filename, md5, fileSize, ext, type='audio', nos_product=3, bucket=BUCKET, local=False,
                    cookies=None):
        '''移动端 - 云盘占位

        Args:
            filename (str): 文件名
            md5 (str): 文件 MD5
            fileSize (str): 文件大小
            ext (str): 文件拓展名
            type (str, optional): 上传类型. Defaults to 'audio'.
            nos_product (int, optional): APP类型. Defaults to 3.
            bucket (str, optional): 转存bucket. Defaults to 'jd-musicrep-privatecloud-audio-public'.
            local (bool, optional): 未知. Defaults to False.

        Returns:
            dict
        '''
        data = {"type": str(type), "nos_product": str(nos_product), "md5": str(md5),
                "local": str(local).lower(), "filename": str(filename), "fileSize": str(fileSize),
                "ext": str(ext), "bucket": str(bucket), "checkToken": GenerateCheckToken()}
        url = self.uri_e + '/nos/token/alloc'
        payload = self.api.eapi_encrypt(b'/api/nos/token/alloc', data)
        return self.api.request('POST', url, {'params': payload})

    def SetUploadObject(self, stream, md5, fileSize, objectKey, token, offset=0, compete=True, bucket=BUCKET):
        '''移动端 - 上传内容

        Args:
            stream : bytes / File 等数据体 .e.g open('file.mp3')
            md5 : 数据体哈希
            objectKey : GetNosToken 获得
            token : GetNosToken 获得
            offset (int, optional): 续传起点. Defaults to 0.
            compete (bool, optional): 文件是否被全部上传. Defaults to True.

        Returns:
            dict
        '''
        r = requests.post(
            'http://45.127.129.8/%s/' % bucket + objectKey.replace('/', '%2F'),
            data=stream,
            params={
                'version': '1.0',
                'offset': offset,
                'complete': str(compete).lower()
            },
            headers={
                'x-nos-token': token,
                'Content-MD5': md5,
                'Content-Type': 'cloudmusic',
                'Content-Length': str(fileSize)
            }
        )
        return json.loads(r.text)

    def SetUploadCloudInfo(self, resourceId, songid, md5, filename, song='.', artist='.', album='.', bitrate=128,
                           cookies=None):
        '''移动端 - 云盘资源提交

        注：
            - MD5 对应文件需已被 SetUploadObject 上传
            - song 项不得包含字符 .和/

        Args:
            resourceId (str): GetNosToken 获得
            songid (str): GetCheckCloudUpload 获得
            md5 (str): 文件MD5哈希
            filename (str): 文件名
            song (str, optional): 歌名 / 标题. Defaults to ''.
            artist (str, optional): 艺术家名. Defaults to ''.
            album (str, optional): 专辑名. Defaults to ''.
            bitrate (int, optional): 音频 - 比特率. Defaults to 0.

        WIP - 封面ID,歌词ID 等

        Returns:
            dict
        '''
        data = {"resourceId": str(resourceId), "songid": str(songid), "md5": str(md5),
                "filename": str(filename), "song": str(song), "artist": str(artist),
                "album": str(album), "bitrate": bitrate}
        url = self.uri_e + '/upload/cloud/info/v2'
        payload = self.api.eapi_encrypt(b'/api/upload/cloud/info/v2', data)
        return self.api.request('POST', url, {'params': payload})

    def SetPublishCloudResource(self, songid, cookies=None):
        '''移动端 - 云盘资源发布

        Args:
            songid (str): 来自 SetUploadCloudInfo

        Returns:
            SetUploadCloudInfo
        '''
        data = {"songid": str(songid), "checkToken": GenerateCheckToken()}
        url = self.uri_e + '/cloud/pub/v2'
        payload = self.api.eapi_encrypt(b'/api/cloud/pub/v2', data)
        return self.api.request('POST', url, {'params': payload})