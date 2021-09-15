import os
import json

from enum import Enum
from notion_api import NotionAPI
from common.webhook_api import (
    SEND_SUCCESS, SEND_FAIL, NO_MSGS, InCommingWebHooks
)


INCOMING_WEBHOOK_API = None
NOTION_API = None


def get_notion_api(notion_api_token):
    global NOTION_API

    if NOTION_API is None:
        NOTION_API = NotionAPI(notion_api_token)

    return NOTION_API


def get_in_comming_webhook_api(in_comming_webhook_url):
    global INCOMING_WEBHOOK_API

    if INCOMING_WEBHOOK_API is None:
        INCOMING_WEBHOOK_API = InCommingWebHooks(in_comming_webhook_url)

    return INCOMING_WEBHOOK_API


class SchemaTable(Enum):
    """ 공지사항 페이지의 Collection 의 각각의 칼럼 이름을 정의 합니다.
    """
    DATE_NAME = '공지일'
    TARGET_NAME = '대상'
    TITLE_NAME = '제목'
    WRITER_NAME = '작성자'
    SEND_CHK_BOX_NAME = '공지 하기'


class NoticeBot(object):
    def __init__(self):
        self.__set_required_setting()
        self.__notice_all_items = []

        self.notion = get_notion_api(self.notion_token)
        self.webhook = get_in_comming_webhook_api(self.incoming_webhook_url)

    def __set_required_setting(self):
        """ Notice Bot 패키지의 루트 디렉토리에서 'conf.json' 파일을 가져와
            아래 필수 항목에 대해 파싱 및 attribute 를 지정합니다.

            아래 필수 항목이 존재하지 않는 경우 init 에 실패합니다.
                1. notion_url : 공지사항이 존재하는 노션 페이지 링크
                2. notion_token: 페이지 수정권한이 있는 계정에 대한 토큰 정보
                3. incoming_webhook_url : 슬랙으로 알림을 전송하기 위해
                   특정 채널에 설정된 incoming webhooks 에 대한 url 정보보
        """
        required_conf_value = [
            'notion_url', 'notion_token', 'incoming_webhook_url'
        ]

        # TODO. 절대 경로 기준으로 변경 필요
        conf_dict = json.load(
            open(os.path.join('../', 'conf.json'))
        )

        # validation check conf.json values
        for val in required_conf_value:
            if val not in conf_dict:
                raise Exception(
                    'Invalid conf.json file '
                    '["{}" is mandatory value]'.format(val)
                )

        # make attribute
        for key, val in conf_dict.items():
            setattr(self, key, val)

    def set_notice_page_items(self):
        """ @self.notion_url 정보를 사용하여, page block obj를 받아옵니다.
            받아온 obj 에서 'collection' block 에 해당하는 항목을 가져와,
            각각의 모든 칼럼을 @self.__notice_all_items 에 저장합니다.
        """
        try:
            notice_page = self.notion.get_page_block_from_url(self.notion_url)

            self.__notice_all_items = (
                self.notion.get_collection_item_list(notice_page)
            )

        except Exception as e:
            raise Exception(
                'Failed get notion page collections [msg: {}]'.format(e)
            )

    def get_notice_page_items(self):
        """ 필요시 정의 """
        pass

    def __iter_notice_items(self, items):
        """ 'collection' block 의 각 칼럼 정보를 가진 값 (@items) 을 입력 받아
            '공지 하기 (@SEND_CHK_BOX_NAME)' 체크박스가 True 인 항목만 찾고
            해당 항목만 iteration 해줍니다.
        """
        for item in items:
            is_need_notice = self.notion.get_collection_item_property(
                item, SchemaTable.SEND_CHK_BOX_NAME.value
            )

            if is_need_notice is True:
                yield item

    def __get_target_item_list(self):
        """ 'collection' block 의 각 칼럼 정보를 가진 값 (@self.__notice_all_items)
            에서 slack 으로 알림 전송이 필요한 item 을 iteration 하여
            @target_list에 저장합니다.
        """
        target_list = []
        for item in self.__iter_notice_items(self.__notice_all_items):
            target_list.append(item)

        return target_list

    def __make_block_fmt_slack_msg(self, item):
        """ 'collection' block 의 특정 칼럼 (@item) 에서
            일부 값만 파싱하여, slack block formating 에 맞게 변환 하여 반환 합니다.

            slack block 포맷 형태는 'block_fmt.json' 외부 파일에 따로 정의되어있음
        """
        def get_collection_obj(schema):
            return self.notion.get_collection_item_property(item, schema)

        # date (작성 날짜)
        date = '<날짜 없음>'
        date_obj = get_collection_obj(SchemaTable.DATE_NAME.value)
        if date_obj:
            date = str(date_obj.start)

        # title (공지 제목)
        title = '<제목 없음>'
        title_obj = get_collection_obj(SchemaTable.TITLE_NAME.value)
        if title_obj:
            title = str(title_obj)

        # writer (작성자)
        writer = '<작성자 없음>'
        writer_obj = get_collection_obj(SchemaTable.WRITER_NAME.value)
        if writer_obj:
            writer = ', '.join(
                [writer.full_name for writer in writer_obj]
            )

        # target (공지 대상)
        target = '<대상 없음>'
        target_obj = get_collection_obj(SchemaTable.TARGET_NAME.value)
        if target_obj:
            target = ', '.join(target_obj)

        # content page id (공지 페이지 링크)
        page_id = str(item.id).replace('-', '')

        # get json format and convert
        json_variable_table = {
            '${date}': date,
            '${title}': title,
            '${writer}': writer,
            '${target}': target,
            '${link}': 'https://www.notion.so/{}'.format(page_id)
        }

        block_dict = json.load(
            open(os.path.join('../', 'block_fmt.json'))
        )

        block_fmt_str = json.dumps(block_dict)
        for json_variable, replace_value in json_variable_table.items():
            block_fmt_str = block_fmt_str.replace(
                json_variable, replace_value
            )

        new_block_dict = json.loads(block_fmt_str)

        return new_block_dict

    def __send_to_slack(self, item):
        """
            전송할 특정 칼럼 정보 (@item) 에서, 필요한 값을 추출하여
            slack에 전송할 block 형식의 포맷 생성 및 webhook api를 통해
            채널로 전송합니다.

            참고:
                - block 포맷형태의 메세지는 아래 Block Kit Builder를 참고
                  (https://app.slack.com/block-kit-builder/)

        """
        data = {}
        data['blocks'] = self.__make_block_fmt_slack_msg(item)

        return self.webhook.send_msg(**data)

    def check(self):
        """ 메인 함수로써, 'conf.json' 파일에 입력된 설정 정보를 토대로
            slack 으로 전송이 필요한 항목 파싱 및 메세지 생성 후 특정 채널로 전송 합니다.

            NOTICE.
                전송이 필요한 항목의 판단은 Notion collection block에 추가된
                @SEND_CHK_BOX_NAME 이름을 가진 칼럼의 'checkbox' 여부로 판단하게
                됩니다.

                eg. @SEND_CHK_BOX_NAME 이름을 가진 칼럼의 'checkbox' 항목
                    이 체크되어있는 경우 메세지 전송 -> 해당 'checkbox' 는 체크 해제
        """
        target_list = self.__get_target_item_list()
        for target_item in target_list:
            res = self.__send_to_slack(target_item)  # TODO. 현재 @res 값은 사용하지 않음

            # 'checkbox' 항목 체크 해제 (False)
            self.notion.set_collection_item_property(
                target_item,
                SchemaTable.SEND_CHK_BOX_NAME.value,
                False
            )


def main():
    try:
        nb = NoticeBot()
        nb.set_notice_page_items()
        nb.check()

    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
