import shutil
from base64 import b64encode
from enum import IntEnum
from functools import wraps
from http import HTTPStatus
from pathlib import Path

from cyberdrop_dl.base_functions.base_functions import FILE_FORMATS, logger
from cyberdrop_dl.base_functions.data_classes import MediaItem
from cyberdrop_dl.base_functions.error_classes import DownloadFailure


class CustomHTTPStatus(IntEnum):
    WEB_SERVER_IS_DOWN = 521
    IM_A_TEAPOT = 418


async def allowed_filetype(media: MediaItem, block_images: bool, block_video: bool, block_audio: bool, block_other: bool):
    """Checks whether the enclosed file is allowed to be downloaded"""
    ext = media.ext
    if block_images and ext in FILE_FORMATS["Images"]:
        return False
    if block_video and ext in FILE_FORMATS["Videos"]:
        return False
    if block_audio and ext in FILE_FORMATS["Audio"]:
        return False
    if block_other and ext not in (FILE_FORMATS["Images"] | FILE_FORMATS["Videos"] | FILE_FORMATS["Audio"]):
        return False
    return True


async def basic_auth(username, password):
    token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'


async def check_free_space(required_space_gb: int, download_directory: Path) -> bool:
    """Checks if there is enough free space on the drive to continue operating"""
    free_space = shutil.disk_usage(download_directory.parent).free
    free_space_gb = free_space / 1024 ** 3
    return free_space_gb >= required_space_gb


async def is_4xx_client_error(status_code: int) -> bool:
    """Checks whether the HTTP status code is 4xx client error"""
    return HTTPStatus.BAD_REQUEST <= status_code < HTTPStatus.INTERNAL_SERVER_ERROR


def retry(f):
    """This function is a wrapper that handles retrying for failed downloads"""

    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        while True:
            try:
                return await f(self, *args, **kwargs)
            except DownloadFailure as e:
                media = args[1]
                url_path = args[2]
                if not self.disable_attempt_limit and self.current_attempt[url_path] >= self.allowed_attempts - 1:
                    await self.output_failed(media, e)
                    logger.debug('Skipping %s...', media.url, exc_info=True)
                    self.files.failed_files += 1
                    await self.failed_files_progress()
                    return None
                logger.debug(e.message)
                logger.debug(f'Retrying ({self.current_attempt[url_path]}) {media.url}...')
                self.current_attempt[url_path] += 1

    return wrapper
