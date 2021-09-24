import os

from pathlib import Path


def get_package_root_path():
    """ 현재 'constants.py' 파일이 위치한 경로를 기준으로
        slack bot 패키지 루트 디렉토리 경로를 찾아 반환 합니다.
    """
    cur_file_path = Path(os.path.abspath(__file__))
    return cur_file_path.parent.parent.absolute()


PACKAGE_ROOT_PATH = get_package_root_path()
NOTION_BOT_RESOURCE_DIR_NAME = 'notion_bot/resource'
NOTION_BOT_RESOURCE_PATH = '/'.join(
    [str(PACKAGE_ROOT_PATH), NOTION_BOT_RESOURCE_DIR_NAME]
)
