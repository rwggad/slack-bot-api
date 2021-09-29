import os
import json

from notion_api import NotionAPI, NotionDate, User
from common.logger import get_logger
from common.constants import NOTION_BOT_RESOURCE_PATH
from common.error import GetNotionBlockError
from common.webhook_api import (
    SEND_SUCCESS, SEND_FAIL, NO_MSGS, InCommingWebHooks
)

LOGGER = get_logger('notion.notion_bot')
CONF_DIR = NOTION_BOT_RESOURCE_PATH + '/notion_confs'


class NotionBot(object):
    def __init__(self, webhook_url):
        self.webhook = InCommingWebHooks(webhook_url)

        self.schema_table = {}

    def send_msg_to_slack(self, text=None, blocks=None):
        """
            간단한 문장 (@text) 또는 블럭형태 (@blocks) 메시지 를
            webhook api를 통해 지정된 slack 채널로 전송합니다.

            참고:
            - https://api.slack.com/messaging/webhooks#posting_with_webhooks
            - https://app.slack.com/block-kit-builder/
        """
        if not text and not blocks:
            raise Exception('Text or block objects must exist.')

        data = {}

        if text:
            data['text'] = text

        if blocks:
            data['blocks'] = blocks

        return self.webhook.send_msg(**data)

    def set_schema_table(self, schema_conf_dict):
        """ 'slack/send_type' 설정이 ' block' 인 경우,
            'slack/block_format' 설정 정보를 @self.schmea_table에 저장 합니다.
        """
        self.schema_table = schema_conf_dict

    def set_block_item(self):
        """ need overriding """
        pass

    def get_target_block_item(self, trigger):
        """ need overriding """
        pass

    def make_text_msg(self, *args, **kwargs):
        """ need overriding """
        pass

    def make_block_msg(self, *args, **kwargs):
        """ need overriding """
        pass


class CollectionPageNotiBot(NotionBot):
    """ 특정 Notion 페이지의 'collection' (이하 Coll) 블럭에서,
        대한 수정사항을 Row 항목에 대한 수정사항을 아래의 trigger 에 맞게 체크하여
        슬랙으로 노티하여 줍니다.

        - trigger
            conf.json 파일에 정의 ('schema/trigger')
            (체크박스 칼럼이며, 각각의 행에서 체크박스 체크 유무로 노티여부를 판단)
    """

    def __init__(self, webhook_url, notion_token, notion_url):
        super(CollectionPageNotiBot, self).__init__(webhook_url)

        self.notion = NotionAPI(notion_token)
        self.notion_url = notion_url

        self.all_row_items = []

    def set_block_item(self):
        """ Notion URL (@self.notion_url) 에 해당하는 페이지의
            Coll 블럭에 대한 각각의 Row 항목에 대한 오브젝트를 클래스  attribute
            (@all_row_items) 에 저장합니다.
        """
        try:
            page = self.notion.get_page_block_from_url(self.notion_url)

            self.all_row_items = (
                self.notion.get_collection_item_list(page)
            )

        except Exception as e:
            raise Exception(
                'Set collection block failed ({})'.format(e)
            )

    def get_target_block_item(self, trigger):
        """ Coll 블럭에 대한 각각의 Row 항목이 저장된 리스트 (@items) 에서
            Trigger가 되는 체크박스가 True (체크됨) 인 항목을 iteration 하여
            리스트에 저장 및 반환 합니다.

            TODO. 개선 필요 (꼭 필요한가?..)
        """
        def iter_target_item(items):
            for item in items:
                is_need_notice = (
                    self.notion.get_collection_item_property(item, trigger)
                )

                if is_need_notice is True:
                    yield item

        target_items = []
        for item in iter_target_item(self.all_row_items):
            target_items.append(item)

            # Trigger 체크박스 해제
            self.notion.set_collection_item_property(item, trigger, False)

        return target_items

    def make_block_msg(self, item):
        """ Slack block 메세지 포맷에 맞게 전송하고자 하는 메세지 포맷을 생성합니다.

            - conf.json 의 'schema/fmt_variable' 에 정의된 key/value 기준으로
              Coll 블럭의 각각의 행에 매칭되는 칼럼 값을 가져와서 string 형태로 변환 및
              메세지 포맷을 생성
        """
        def get_collection_obj(col_name):
            """ Coll 블럭의 각각의 행 정보를 가진 object(@item) 에서,
                칼럼 이름 (@col_name)에 해당하는 값에 대한 notion object를 가져와 반환
                합니다.
            """
            return self.notion.get_collection_item_property(item, col_name)

        def get_collection_obj_value(obj):
            """ Notion object 의 타입에 따라 해당되는 값을 string 형태로 변환 하여
                반환 합니다.

                TODO. 현재는 'Notion Date', 'User', 'string' 형태에 대해서만
                      변환 작업을 하고있으며, 필요에 따라 추가 작업이 필요함
            """
            if isinstance(obj, list):  # object list
                value_list = []
                for _obj in obj:
                    value_list.append(get_collection_obj_value(_obj))

                return ', '.join(value_list)

            elif isinstance(obj, str):  # general object
                return obj

            elif isinstance(obj, NotionDate):  # date object
                return str(obj.start)

            elif isinstance(obj, User):  # user object
                return str(obj.full_name)

            else:
                return str(obj)


        schmea_fmt_f_name = self.schema_table['file']
        schmea_fmt_var_dict = self.schema_table['variable_block']

        # table 정보에 conf json에 정의된 변수값 추가
        json_var_table = {}
        for s_var, s_name in schmea_fmt_var_dict.items():
            cobj = get_collection_obj(s_name)

            key = '${{{var}}}'.format(var=s_var)
            value = get_collection_obj_value(cobj)

            json_var_table[key] = value

        # table 정보에 페이지 link 추가
        page_id = str(item.id).replace('-', '')
        json_var_table.update(
            {'${link}': 'https://www.notion.so/{}'.format(page_id)}
        )

        # table 정보에 comment 추가 (TODO. notion page의 comment 값 가져올 수 있도록)
        json_var_table.update({
            '${comment}': '해당되는 사업부는 위 공지를 참고하여 업무 숙지 해주시기 바랍니다.'
        })

        # json 포맷 파일을 가져오고, 정의된 variable에 table 정보 추가
        block_dict = json.load(
            open(os.path.join(CONF_DIR, schmea_fmt_f_name))
        )

        block_fmt_str = json.dumps(block_dict)
        for json_var, value in json_var_table.items():
            block_fmt_str = block_fmt_str.replace(
                json_var, str(value)
            )

        new_block_dict = json.loads(block_fmt_str)

        return new_block_dict
