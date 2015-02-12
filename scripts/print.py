#!/usr/bin/env python3

import datetime
import json

class Print():
    def __init__(self):
        ''' Init whatever you need here.
            For example, a datebase connection
        '''
        pass

    def do_any(self, text):
        print(">>>>>> %s \n%s" % (datetime.datetime.now(),
                                  json.dumps(text, indent=2)))

    def do_tweet(self, message):
        print(">>>> %s \n%s: %s" % (message['created_at'],
                                    message['user']['screen_name'],
                                    message['text']))

handler = Print()
