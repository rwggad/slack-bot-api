import os
import sys
import time
import argparse

from common.utils import print_execution_func
from common.logger import get_logger
from common.error import InitError, ConfParseError, SpawnError

from resource.config import CONFIG_LIST
from notion_slack_bot import CONF_DIR, CollectionPageNotiBot

LOGGER = get_logger('notion.manager')

DAEMON_PID_PATH = '/var/run/slackbot_daemon.pid'


class Manager(object):
    """ 패키지의 'resource/notion_conf' 디렉토리에 위치한 각각의 conf.json 값을
        파싱 및 @nobjs 리스트에 저장하여 관리 합니다.
    """

    def __init__(self):
        self.__nobjs = []  # notion object list

    def __validation_conf(self, conf_dict):
        """ CONFIG_LIST에 정의된 각각의 설정값에 대한 유효성 검증을 수행 합니다.
        """
        mandatory_errmsg_fmt ='The essential element is missing ({})'

        def validate_webhook_conf(webhook_conf):
            if not webhook_conf:
                raise ConfParseError(mandatory_errmsg_fmt.format('webhook'))

            required_conf_value = ['incoming_url']
            for _value in required_conf_value:
                if webhook_conf.get(_value):
                    continue

                path = 'webhook/{}'.format(_value)
                raise ConfParseError(mandatory_errmsg_fmt.format(path))

        def validate_notion_conf(notion_conf):
            LOGGER.error(notion_conf)
            if not notion_conf:
                raise ConfParseError(mandatory_errmsg_fmt('notion'))

            required_conf_value = ['token', 'page_type', 'page_url', 'trigger']
            for _value in required_conf_value:
                if notion_conf.get(_value):
                    continue

                path = 'notion/{}'.format(_value)
                raise ConfParseError(mandatory_errmsg_fmt.format(path))

        def validate_slack_conf(slack_conf):
            if not slack_conf:
                raise ConfParseError(mandatory_errmsg_fmt('slack'))

            required_conf_value = ['send_type']
            for _value in required_conf_value:
                if slack_conf.get(_value):
                    continue

                path = 'slack/{}'.format(_value)
                raise ConfParseError(mandatory_errmsg_fmt.format(path))


            if slack_conf['send_type'] == 'block':
                if 'block_format' not in slack_conf:
                    path = 'slack/block_format'
                    raise ConfParseError(mandatory_errmsg_fmt.format(path))

        validate_webhook_conf(conf_dict.get('webhook'))
        validate_notion_conf(conf_dict.get('notion'))
        validate_slack_conf(conf_dict.get('slack'))

        LOGGER.info('- Config valid check OK')

    def __spawn_nmod(self, nobj):
        """ CONFIG_LIST에 정의된 값의 'page_type' 에 맞은 Notion Bot Module
            인스턴스를 생성 후, @nobj에 저장합니다. (이 후 @self.nobjs 리스트에 관리 )
        """
        webhook_conf = nobj['conf_dict']['webhook']
        notion_conf = nobj['conf_dict']['notion']

        notion_token = notion_conf['token']
        notion_page_type = notion_conf['page_type']
        notion_url = notion_conf['page_url']

        webhook_url = webhook_conf['incoming_url']

        if notion_page_type == 'collection':
            mod = CollectionPageNotiBot(webhook_url, notion_token, notion_url)

        else:
            raise SpawnError(
                'Invalid notion page type "{}"'.format(notion_page_type)
            )

        nobj['mod'] = mod

        LOGGER.info('- Make notion bot module: ({})'.format(nobj['mod']))

    def __init_nmod(self, nobj):
        slack_conf = nobj['conf_dict']['slack']
        slack_send_type = slack_conf['send_type']

        if slack_send_type == 'block':
            nobj['mod'].set_schema_table(slack_conf['block_format'])

    def init(self):
        try:
            if not CONFIG_LIST or not isinstance(CONFIG_LIST, list):
                raise ConfParseError('Missing config list')

            for __conf_dict in CONFIG_LIST:
                self.__validation_conf(__conf_dict)

                nobj = {}
                nobj['conf_dict'] = __conf_dict

                self.__spawn_nmod(nobj)
                self.__init_nmod(nobj)
                self.__nobjs.append(nobj)

        except ConfParseError as e:
            raise InitError('Conf parse failed ({})'.format(e))

        except SpawnError as e:
            raise InitError('Spawn module failed ({})'.format(e))

        except Exception as e:
            raise InitError('Init failed: {}'.format(e))

        LOGGER.info('- Init OK')
        LOGGER.info('- Check target count: {}'.format(len(self.__nobjs)))

    def check(self):
        for nobj in self.__nobjs:
            notion_conf = nobj['conf_dict']['notion']
            slack_conf = nobj['conf_dict']['slack']

            notion_trigger = notion_conf['trigger']
            slack_send_type = slack_conf['send_type']

            mod = nobj.get('mod')
            mod.set_block_item()

            for item in mod.get_target_block_item(notion_trigger):
                if slack_send_type == 'text':
                    msg = mod.make_text_msg(item)
                    mod.send_msg_to_slack(text=msg)

                elif slack_send_type == 'block':
                    msg = mod.make_block_msg(item)
                    mod.send_msg_to_slack(blocks=msg)


class Daemon(object):
    def __init__(self):
        self.manager = Manager()

    def __run_manager(self):
        while True:
            try:
                self.manager.check()

            except Exception as e:
                LOGGER.info(
                    'Manager check failed ({})'.format(e)
                )

            time.sleep(5)

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

                self.manager.init()

                __daemon_pid = str(os.getpid())
                with open(DAEMON_PID_PATH, 'w') as f:
                    f.write(__daemon_pid)

                LOGGER.info('Start daemon (pid:{})'.format(__daemon_pid))

        except Exception as e:
            raise Exception('Start daemon failed ({})'.format(e))

        self.__run_manager()

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
