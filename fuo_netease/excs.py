from feeluown.excs import ProviderIOError


class NeteaseIOError(ProviderIOError):
    def __init__(self, message):
        super().__init__(message, provider='netease')
