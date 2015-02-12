#!/usr/bin/env python3

import datetime
import json

class Print():
    def __init__(self):
        ''' Init whatever you need here.
            For example, a datebase connection
        '''
        pass

    def do_tweet(self, text):
        print(">>>>>>",
              str(datetime.datetime.now()),
              "\n",
              json.dumps(text, indent=2))

handler = Print()
