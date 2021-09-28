import requests

from common.logger import get_logger

SEND_SUCCESS = 1
SEND_FAIL = 0
NO_MSGS = -1

LOGGER = get_logger('webhook')


class WebHooksAPI(object):
    def __init__(self, url):
        if not url:
            raise Exception('URL Required Options')

        self.url = url

    def post(self, **kwargs):
        res = requests.post(self.url, **kwargs)
        return res


class InCommingWebHooks(WebHooksAPI):
    def __init__(self, url):
        super(InCommingWebHooks, self).__init__(url)

        self.json_data = {}

    def send_msg(self, **kwargs):
        if not kwargs:
            return NO_MSGS

        self.json_data.update(kwargs)

        try:
            res = self.post(json=self.json_data)
            LOGGER.info('Success send to slack [response code: {}]'.format(res))

        except Exception as e:
            LOGGER.error('Failed send to slack [msg: {}]'.format(e))
            return SEND_FAIL

        finally:
            self.json_data = {}

        return SEND_SUCCESS


class OutgoingWebHooks(WebHooksAPI):
    pass
