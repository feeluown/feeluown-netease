import time, json, requests
from requests.models import Response
from .crypto import RandomString, GenerateCheckToken, EapiDecrypt, EapiEncrypt, AbroadDecrypt
BUCKET = 'jd-musicrep-privatecloud-audio-public'


def parse(url):
    import urllib.parse
    return urllib.parse.urlparse(url)


HOST        = 'https://music.163.com/'
UA_EAPI     = 'NeteaseMusic/7.2.24.1597753235(7002024);Dalvik/2.1.0 (Linux; U; Android 11; Pixel 2 XL Build/RP1A.200720.009)'
CONFIG_EAPI = {
    'appver': '7.2.24','buildver':'7002024','channel':'offical','deviceId': RandomString(8),
    'mobilename' : 'Pixel2XL','os': 'android','osver':'10.1','resolution': '2712x1440','versioncode': '240'
}
def EapiCryptoRequest(url, plain, cookies):
    '''Eapi - 适用于 新版客户端绝大部分 APIs'''
    cookies = dict(cookies, **{
        **CONFIG_EAPI,
        'requestId':f'{int(time.time() * 1000)}_0233',
    })
    payload = {
        **plain,
        'header': json.dumps(cookies)
    }

    request = requests.post(
        HOST + url,
        headers = {
            'User-Agent': UA_EAPI,
            'Referer': None
        },
        cookies=cookies,
        data={**EapiEncrypt(parse(url).path.replace('/eapi/', '/api/'), json.dumps(payload))}
    )
    return request


def GetNosToken(filename, md5, fileSize, ext, type='audio', nos_product=3, bucket=BUCKET, local=False, cookies=None):
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
    eapi = '/eapi/nos/token/alloc'
    data = {"type": str(type), "nos_product": str(nos_product), "md5": str(md5),
            "local": str(local).lower(), "filename": str(filename), "fileSize": str(fileSize),
            "ext": str(ext), "bucket": str(bucket), "checkToken": GenerateCheckToken()}
    request = EapiCryptoRequest(eapi, data, cookies)
    try:
        rsp = EapiDecrypt(request.content).decode()
    except:
        rsp = request.content
    try:
        payload = rsp.text if isinstance(rsp, Response) else rsp
        payload = payload.decode() if not isinstance(payload, str) else payload
        payload = json.loads(payload.strip('\x10'))  # plaintext responses are also padded...
        if 'abroad' in payload and payload['abroad']:  # addresses #15
            real_payload = AbroadDecrypt(payload['result'])
            payload = json.loads(real_payload)
        return payload
    except json.JSONDecodeError:
        return rsp


def SetUploadObject(stream, md5, fileSize, objectKey, token, offset=0, compete=True, bucket=BUCKET):
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


def GetCheckCloudUpload(md5, ext='', length=0, bitrate=0, songId=0, version=1, cookies=None):
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
    eapi = '/eapi/cloud/upload/check'
    data = {"songId": str(songId), "version": str(version), "md5": str(md5),
            "length": str(length), "ext": str(ext), "bitrate": str(bitrate),
            "checkToken": GenerateCheckToken()}
    request = EapiCryptoRequest(eapi, data, cookies)
    try:
        rsp = EapiDecrypt(request.content).decode()
    except:
        rsp = request.content
    try:
        payload = rsp.text if isinstance(rsp, Response) else rsp
        payload = payload.decode() if not isinstance(payload, str) else payload
        payload = json.loads(payload.strip('\x10'))  # plaintext responses are also padded...
        if 'abroad' in payload and payload['abroad']:  # addresses #15
            real_payload = AbroadDecrypt(payload['result'])
            payload = json.loads(real_payload)
        return payload
    except json.JSONDecodeError:
        return rsp


def SetUploadCloudInfo(resourceId, songid, md5, filename, song='.', artist='.', album='.', bitrate=128, cookies=None):
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
    eapi = '/eapi/upload/cloud/info/v2'
    data = {"resourceId": str(resourceId), "songid": str(songid), "md5": str(md5),
            "filename": str(filename), "song": str(song), "artist": str(artist),
            "album": str(album), "bitrate": bitrate}
    request = EapiCryptoRequest(eapi, data, cookies)
    try:
        rsp = EapiDecrypt(request.content).decode()
    except:
        rsp = request.content
    try:
        payload = rsp.text if isinstance(rsp, Response) else rsp
        payload = payload.decode() if not isinstance(payload, str) else payload
        payload = json.loads(payload.strip('\x10'))  # plaintext responses are also padded...
        if 'abroad' in payload and payload['abroad']:  # addresses #15
            real_payload = AbroadDecrypt(payload['result'])
            payload = json.loads(real_payload)
        return payload
    except json.JSONDecodeError:
        return rsp


def SetPublishCloudResource(songid, cookies=None):
    '''移动端 - 云盘资源发布

    Args:
        songid (str): 来自 SetUploadCloudInfo

    Returns:
        SetUploadCloudInfo
    '''
    eapi = '/eapi/cloud/pub/v2'
    data = {"songid": str(songid), "checkToken": GenerateCheckToken()}
    request = EapiCryptoRequest(eapi, data, cookies)
    try:
        rsp = EapiDecrypt(request.content).decode()
    except:
        rsp = request.content
    try:
        payload = rsp.text if isinstance(rsp, Response) else rsp
        payload = payload.decode() if not isinstance(payload, str) else payload
        payload = json.loads(payload.strip('\x10'))  # plaintext responses are also padded...
        if 'abroad' in payload and payload['abroad']:  # addresses #15
            real_payload = AbroadDecrypt(payload['result'])
            payload = json.loads(real_payload)
        return payload
    except json.JSONDecodeError:
        return rsp