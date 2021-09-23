from typing import Collection
from notion.client import NotionClient
from notion.block import *
from notion.collection import *
from notion.user import *


class NotionAPI(NotionClient):
    def __init__(self, token):
        super(NotionAPI, self).__init__(token_v2=token)

    def __get_block(self, page, block_type, match_title=''):
        # TODO block type valid check

        all_type_block = [
            _child for _child in page.children
                if isinstance(_child, block_type)
        ]

        if match_title:
            all_type_block = list(
                filter(
                    (lambda b: b.title == match_title), all_type_block
                )
            )

        return all_type_block

    def get_text_block(self, page, match_text=''):
        return self.__get_block(page, TextBlock, match_text)

    def get_page_block_from_url(self, url):
        return self.get_block(url)

    def get_page_block(self, page, match_text=''):
        return self.__get_block(page, PageBlock, match_text)

    def get_todo_block(self, page, match_text=''):
        return self.__get_block(page, TodoBlock, match_text)

    def get_bullet_list_block(self, page, match_text=''):
        return self.__get_block(page, BulletedListBlock, match_text)

    def get_number_list_block(self, page, match_text=''):
        return self.__get_block(page, NumberedListBlock, match_text)

    def get_toggle_block(self, page, match_text=''):
        return self.__get_block(page, ToggleBlock, match_text)

    def get_quote_block(self, page, match_text=''):
        return self.__get_block(page, QuoteBlock, match_text)

    def get_divider_block(self, page, match_text=''):
        return self.__get_block(page, DividerBlock, match_text)

    def get_callout_block(self, page, match_text=''):
        return self.__get_block(page, CalloutBlock, match_text)

    def get_image_block(self, page, match_text=''):
        return self.__get_block(page, ImageBlock, match_text)

    def get_web_bookmark_block(self, page, match_text=''):
        return self.__get_block(page, BookmarkBlock, match_text)

    def get_video_block(self, page, match_text=''):
        return self.__get_block(page, VideoBlock, match_text)

    def get_audio_block(self, page, match_text=''):
        return self.__get_block(page, AudioBlock, match_text)

    def get_code_block(self, page, match_text=''):
        return self.__get_block(page, CodeBlock, match_text)

    def get_file_block(self, page, match_text=''):
        return self.__get_block(page, FileBlock, match_text)

    def get_collection_block(self, page):
        page_collection = page.collection
        if not page_collection:
            raise Exception('Empty notice page')

        return page_collection

    def get_collection_item_list(self, page):
        collection = self.get_collection_block(page)

        return collection.get_rows()

    def get_collection_item_property(self, item, prop_name):
        try:
            property_val = item.get_property(prop_name)

        except Exception as e:
            raise Exception('Failed get property [msg: {}]'.format(e))

        return property_val

    def set_collection_item_property(self, item, prop_name, prop_value):
        try:
            item.set_property(prop_name, prop_value)

        except Exception as e:
            raise Exception('Failed set property [msg: {}]'.format(e))
