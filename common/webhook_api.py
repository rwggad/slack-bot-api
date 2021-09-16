import requests


SEND_SUCCESS = 1
SEND_FAIL = 0
NO_MSGS = -1


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
            print('Success send to slack [response code: {}]'.format(res))

        except Exception as e:
            print('Failed send to slack [msg: {}]'.format(e))
            return SEND_FAIL

        return SEND_SUCCESS


class OutgoingWebHooks(WebHooksAPI):
    pass