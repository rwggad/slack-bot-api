import os
import sys
import json
import time

from notion_api import NotionAPI, NotionDate, User
from common.utils import print_execution_func
from common.logger import get_logger
from common.error import (
    InitError, ConfParseError, SpawnError, GetNotionBlockError
)
from common.webhook_api import (
    SEND_SUCCESS, SEND_FAIL, NO_MSGS, InCommingWebHooks
)
from common.constants import NOTION_BOT_RESOURCE_PATH


LOGGER = get_logger('notion.main')
CONF_DIR = NOTION_BOT_RESOURCE_PATH + '/notion_confs'


class NotionBot(object):
    def __init__(self, webhook_url):
        self.webhook = InCommingWebHooks(webhook_url)

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

    def set_block_item(self):
        """ need overriding """
        pass

    def get_block_item(self):
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

        self.schema_table = {}

        self.all_row_items = []

    def set_schema_table(self, schema_conf_dict):
        """ conf.json 파일에서, 'schema' 부분을 파싱하여,
            아래 클래스 attribute에 저장합니다.
        """
        self.schema_table = schema_conf_dict
        # TODO. validate check

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

    def get_block_item(self):
        """ Coll 블럭에 대한 각각의 Row 항목이 저장된 리스트 (@items) 에서
            Trigger가 되는 체크박스가 True (체크됨) 인 항목을 iteration 하여
            리스트에 저장 및 반환 합니다.
        """
        def iter_target_item(items):
            for item in items:
                is_need_notice = self.notion.get_collection_item_property(
                    item, self.schema_table['trigger']
                )

                if is_need_notice is True:
                    yield item

        if not self.schema_table:
            raise GetNotionBlockError(
                'The schema table is not defined\n'
                '(Can be defined as a "set_back_table" function)'
            )

        target_items = []
        for item in iter_target_item(self.all_row_items):
            target_items.append(item)

            # Trigger 체크박스 해제
            self.notion.set_collection_item_property(
                item,
                self.schema_table['trigger'],
                False
            )

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


        schmea_fmt_f_name = self.schema_table['fmt_file_name']
        schmea_fmt_var_dict = self.schema_table['fmt_variable']

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


class manager(object):
    """ 패키지의 'resource/notion_conf' 디렉토리에 위치한 각각의 conf.json 값을
        파싱 및 @nobjs 리스트에 저장하여 관리 합니다.
    """

    def __init__(self):
        self.__nobjs = []

    def __conf_parse(self, conf_dict, nobj):
        """ conf.json 에 저장된 항목을 파싱 및 유효성 검사를 진행하여, @@nobjs 리스트에
            key / value 형태로 저장 합니다.
        """
        def validate_check():
            required_conf_value = [
                'type',
                'notion_url',
                'notion_token',
                'incoming_webhook_url'
            ]

            # 필수 항목 요소 체크
            for val in required_conf_value:
                if val not in conf_dict:
                    raise ConfParseError('"{}" is mandatory value'.format(val))

            # 'schema' 항목 체크
            if conf_dict['type'] in ['collection_noti']:
                if 'schema' not in conf_dict:
                    raise ConfParseError(
                        '"Schema item is essential '
                        'when using the "{}" type.'.format(
                            conf_dict['type']
                        )
                    )

        # 유효성 검사
        validate_check()

        # 유효성 검사 통과시, 각 conf dict 항목 설정
        for k, v in conf_dict.items():
            nobj[k] = v

    #@print_execution_func
    def __make_nmod(self, conf_dict, nobj):
        """ conf.json 의 'type' 에 정의된 값에 맞는 Notion Bot Module 인스턴스를 생성
            하며, @nobjs 리스트에 저장 합니다.

            TODO. 현재는 'collection' 타입의 블럭만 지원하고 있음
        """
        p_type = conf_dict['type']

        if p_type == 'collection_noti':
            nobj['mod'] = CollectionPageNotiBot(
                nobj['incoming_webhook_url'],
                nobj['notion_token'],
                nobj['notion_url']
            )

        else:
            raise SpawnError('Invalid page type "{}"'.format(p_type))

        LOGGER.info('- Make notion bot module: ({})'.format(nobj['mod']))

    #@print_execution_func
    def init(self):
        try:
            f_list = os.listdir(CONF_DIR)

            for f_name in f_list:
                if not f_name.startswith('conf'):
                    continue

                nobj = {}

                nobj['fp'] = open(os.path.join(CONF_DIR, f_name))

                conf_dict = json.load(nobj['fp'])

                self.__conf_parse(conf_dict, nobj)

                self.__make_nmod(conf_dict, nobj)

                self.__nobjs.append(nobj)

        except ConfParseError as e:
            raise InitError('- Conf parse failed ({}): {}'.format(f_name, e))

        except SpawnError as e:
            raise InitError('- Spawn module failed ({}): {}'.format(f_name, e))

        except Exception as e:
            raise InitError('- Init failed: {}'.format(e))

        LOGGER.info('- Check target count: {}'.format(len(self.__nobjs)))

    #@print_execution_func
    def finalize(self):
        """ @nojbs 에 저장된 각각의 오브젝트에서, file pointer 에 대한 finalize
            처리를 수행합니다.
        """
        for nobj in self.__nobjs:
            if nobj.get('fp'):
                nobj['fp'].close()

    #@print_execution_func
    def check(self):
        for nobj in self.__nobjs:
            mod = nobj.get('mod')

            if nobj.get('schema'):
                mod.set_schema_table(nobj['schema'])

            mod.set_block_item()
            items = mod.get_block_item()

            for item in items:
                text_msg = mod.make_text_msg(item)
                block_msg = mod.make_block_msg(item)

                res = mod.send_msg_to_slack(text_msg, block_msg)

def run_manager():
    LOGGER.info('start notion bot manager')

    m = manager()

    try:
        m.init()

        while True:
            m.check()
            time.sleep(1)

    except Exception as e:
        LOGGER.error(e)

    finally:
        m.finalize()


def start_daemon():
    LOGGER.info('start notion bot daemon')

    try:
        pid = os.fork()

        if pid > 0:
            LOGGER.info('Spawn child process: (pid {})'.format(pid))
            sys.exit()  # 부모 프로세스 종료

    except Exception as e:
        LOGGER.error('Start daemon failed ({})'.format(e))
        sys.exit()

    os.setsid()
    os.open("/dev/null", os.O_RDWR)
    os.dup(0)
    os.dup(0)

    run_manager()


def stop_daemon():
    LOGGER.info('stop notion bot daemon')

    pid = '999999'

    f = open(PID_FILE, 'r')

    for line in f:
        pid = line = line.strip()

    f.close()

    cmd = 'kill ' + pid

    os.system(cmd)


def main():
    try:
        if len(sys.argv) < 2:
            print('Invalid argument')
            return

        if sys.argv[1] == 'start':
            start_daemon()

        elif sys.argv[1] == 'stop':
            stop_daemon()

        else:
            print('Invalid argument')
            return

    except Exception as e:
        LOGGER.error(e)

if __name__ == '__main__':
    main()
