import os
import sys
import json
import time
import argparse

from common.utils import print_execution_func
from common.logger import get_logger
from common.error import InitError, ConfParseError, SpawnError

from notion_slack_bot import CONF_DIR, CollectionPageNotiBot

LOGGER = get_logger('notion.manager')

DAEMON_PID_PATH = '/var/run/slackbot_daemon.pid'


class Manager(object):
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


class Daemon(object):
    def __init__(self):
        self.manager = Manager()

    def __run_manager(self):
        LOGGER.info('Start manager')

        self.manager.init()

        while True:
            self.manager.check()
            time.sleep(1)

    def run(self):
        # running check
        if os.path.isfile(DAEMON_PID_PATH):
            print('Already running daemon')
            return

        # run daemon
        try:
            pid = os.fork()

            if pid > 0:
                sys.exit()  # 부모 프로세스 종료

            else:
                sys.stdout.flush()
                sys.stderr.flush()

                si = open(os.devnull, 'r')
                so = open(os.devnull, 'a+')
                se = open(os.devnull, 'a+')

                os.dup2(si.fileno(), sys.stdin.fileno())
                os.dup2(so.fileno(), sys.stdout.fileno())
                os.dup2(se.fileno(), sys.stderr.fileno())

                __daemon_pid = str(os.getpid())
                with open(DAEMON_PID_PATH, 'w') as f:
                    f.write(__daemon_pid)

                LOGGER.info('Start daemon (pid:{})'.format(__daemon_pid))
                self.__run_manager()


        except Exception as e:
            raise Exception('Start daemon failed ({})'.format(e))

        finally:
            self.manager.finalize()

    def stop(self):
        # running check
        if not os.path.isfile(DAEMON_PID_PATH):
            print('Not running daemon')
            return

        # stop daemon
        try:
            with open(DAEMON_PID_PATH, 'r') as f:
                __daemon_pid = f.read()

            os.remove(DAEMON_PID_PATH)
            os.system('kill -9 {}'.format(__daemon_pid))

        except Exception as e:
            raise Exception('Stop daemon failed ({})'.format(e))

        LOGGER.info('Stop daemon')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--stop', action='store_true')

    return parser.parse_args()


def main():
    args = parse_args()

    try:
        daemon = Daemon()

        if args.start:
            daemon.run()

        elif args.stop:
            daemon.stop()

        else:
            raise Exception('Invalid arguments')

    except Exception as e:
        LOGGER.error(e)


if __name__ == '__main__':
    main()
