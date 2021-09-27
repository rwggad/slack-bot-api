import os
import sys
import json
import time

from common.utils import print_execution_func
from common.logger import get_logger
from common.error import InitError, ConfParseError, SpawnError

from notion_slack_bot import CONF_DIR, CollectionPageNotiBot

LOGGER = get_logger('notion.manager')


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
