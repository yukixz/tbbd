#!/usr/bin/env python3

import json
import traceback
import xmlrpc.client

CLIENT = [
    xmlrpc.client.ServerProxy("http://localhost:12450", allow_none=True)
]


class XMLRPC:
    def do_tweet(self, message):
        data = json.dumps(message)
        for c in CLIENT:
            try:
                c.do_tweet(data)
            except:
                traceback.print_exc()

handler = XMLRPC()
