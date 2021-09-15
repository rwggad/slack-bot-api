import requests


class WebHooksAPI(object):
    def post(self, url, **kwargs):
        if not url:
            raise Exception('URL Required Options')

        res = requests.post(url, **kwargs)
        return res


class InCommingWebHooks(WebHooksAPI):
    def __init__(self, url, ch, usr):
        self.url = url

        self.json_data = {
            "channel": ch,
            "username": usr,
            "icon_emoji": "clock1"
        }

    def send_msg(self, msg):
        if not msg:
            return

        self.json_data['text'] = msg

        try:
            res = self.post(self.url, json=self.json_data)
            print('Success send to slack [response code: {}]'.format(res))

        except Exception as e:
            print('Failed send to slack [msg: {}]'.format(e))


class OutgoingWebHooks(WebHooksAPI):
    pass
