import time

from datetime import datetime
from webhook_api import InCommingWebHooks


INCOMING_URL = ""
CHANNEL_NAME = ""
SLACK_BOT_NAME = ""


def cal_total_second(t):
    return (t.hour * 3600) + (t.minute * 60)


def get_usr_table():
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


def make_send_msg(usr_table):
    msg_list = []
    cur_time = datetime.now()
    cur_time_second = cal_total_second(cur_time)

    for user, user_time in usr_table.items():
        user_time_second = cal_total_second(user_time)

        if cur_time_second >= user_time_second:
            msg_list.append("{U}님 퇴근!".format(U=user))
            continue

        # cal time interval
        time_interval = int((user_time - cur_time).seconds / 60)
        msg_list.append(
            "{U}님 퇴근까지 {H}시간 {M}분 남으셨습니다 ㅎ".format(
                U=user,
                H=str(int(time_interval/60)),
                M=str(int(time_interval%60))
            )
        )

    if msg_list:
        return '\n'.join(msg_list)

    return ''


def run():
    usr_table = get_usr_table()
    if not usr_table:
        return

    print('running timer bot ({})'.format(datetime.now()))

    hook = InCommingWebHooks(INCOMING_URL, CHANNEL_NAME, SLACK_BOT_NAME)
    msg = make_send_msg(usr_table)
    if msg:
        hook.send_msg(msg)


def main():
    run()


if __name__ == "__main__":
    main()
