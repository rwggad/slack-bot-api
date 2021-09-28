from datetime import datetime
from common.webhook_api import InCommingWebHooks


INCOMING_URL = ""


class TimerBot(object):
    HOUR_TO_SEC = 3600
    MINUTE_TO_SEC = 60

    FINISH_FMT = "{U}님 퇴근!"
    H_M_FMT = "{U}님 퇴근까지 {H}시간 {M}분 남으셨습니다 ㅎ"
    M_FMT = "{U}님 퇴근까지 {M}분 남으셨습니다 ㅎ"

    def __init__(self):
        self.__usr_table = {}
        self.__send_msg = ''

    def __get_usr_table(self):
        usr_table = {}
        with open('./usr_data') as f:
            usr_list = f.readlines()

            for usr in usr_list:
                usr_elem = usr.split()
                if len(usr_elem) != 2:
                    continue

                name = usr_elem[0]
                time = usr_elem[1]
                usr_table[name] = datetime.strptime(time,"%H:%M:%S")

        return usr_table

    def set_usr_table(self):
        self.__usr_table = self.__get_usr_table()

    def get_usr_table(self):
        return self.__usr_table

    def __make_send_msg(self):
        def cal_total_second(t):
            return (
                (t.hour * self.HOUR_TO_SEC) + (t.minute * self.MINUTE_TO_SEC)
            )

        msg_list = []
        cur_time = datetime.now()
        cur_time_to_sec = cal_total_second(cur_time)

        for user, user_time in self.__usr_table.items():
            user_time_to_sec = cal_total_second(user_time)

            sec_interval = (user_time_to_sec - cur_time_to_sec)

            if cur_time_to_sec >= user_time_to_sec:
                msg_list.append(self.FINISH_FMT.format(U=user))
                continue

            elif sec_interval <= self.HOUR_TO_SEC:
                msg_list.append(
                    self.M_FMT.format(
                        U=user,
                        M=str(int(sec_interval / self.MINUTE_TO_SEC))
                    )
                )
                continue

            else:
                remain_hour = int(sec_interval / self.HOUR_TO_SEC)
                remain_minute = int(
                    (sec_interval % self.HOUR_TO_SEC) / self.MINUTE_TO_SEC
                )

                msg_list.append(
                    self.H_M_FMT.format(
                        U=user,
                        H=remain_hour,
                        M=remain_minute
                    )
                )
                continue

        if msg_list:
            return '\n'.join(msg_list)

        return ''

    def set_send_msg(self):
        self.__send_msg = self.__make_send_msg()

    def get_send_msg(self):
        return self.__send_msg


def run():
    print('running timer bot ({})'.format(datetime.now()))

    tb = TimerBot()
    tb.set_usr_table()
    tb.set_send_msg()

    hook = InCommingWebHooks(INCOMING_URL)
    hook.send_msg(**{'text': tb.get_send_msg()})


def main():
    run()


if __name__ == "__main__":
    main()

