""" notion bot 관련 config 리스트 포함

    "webhook"                 : 웹훅 관련 설정을 정의

        "incoming_url"        : 노티할 타겟 채널에 추가된 Incoming Webhook Url 링크


    "notion"                  : 노션 관련 설정을 정의

        "token"               : Notion API를 사용하기 위한 TOKEN
                                  - 위 정보는 타켓 페이지의 편집 권한이 있는 사용자의 계정 토큰을 정의 해야합니다.
                                  - 토큰 값 파싱 방법은 (https://github.com/jamalex/notion-py) 를 참고

        "page_url"            : 데몬에서 감지할 특정 페이지 URL

        "page_type"           : 데몬에서 감지할 특정 페이지의 타입
                                  - 현재는 collection 형태의 블럭 페이지만 지원

        "trigger"             : 데몬이 설정된 페이지를 감지 하면서, 노티 여부를 결정하게 될 트리거 정보
                                  - Check Box 형태의 블럭이어야 하며, 블럭에 추가된 이름을 정의


    "slack"                   : Slack 관련 설정을 정의

        "send type"           : "block" 또는 "text" 타입
                                  - "text" 는 일반적인 스트링 메시지
                                  - "block" 은 슬랙에서 제공하는 특정 블럭의 형태의 메세지
                                      - 해당 타입 사용시, 아래의 "block_format" 설정을 함께 추가해야함
                                      - 참고: https://app.slack.com/block-kit-builder/T02EJLHRW65#%7B%22blocks%22:%5B%7B%22type%22:%22divider%22%7D%5D%7D

        "block_format"        : "send_type"이 "block" 일 때, 필수 필요 요소

            "file"            : 블럭 형태가 정의 된 json 파일 이름

            "variable_block"  : json 파일에 ${var_name} 같은 형태로 변수를 추가할 수 있습니다.
                                이후 데몬이 동작할 때, ${var_name} 에 매칭되는 노션 페이지 블럭을 가져와, 해당 값으로 대치 해줍니다.
"""

CONFIG_LIST = [
    {
        "webhook": {
            "incoming_url": "",
        },

        "notion": {
            "token": "",
            "page_type": "collection",
            "page_url": "",
            "trigger": "공지 하기",
        },

        "slack": {
            "send_type": "block",
            "block_format": {
                "file": "block_fmt_1.json",
                "variable_block": {
                    "date": "공지일",
                    "target": "대상",
                    "writer": "작성자",
                    "title": "제목"
                }
            }
        }
    },

    # Second config setting

    # Third config setting

    # ...
]