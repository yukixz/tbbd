#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import redis
from config import *

class Queue():
    def __init__(self, cgroup=None, cname=None):
        ''' Init Queue instance.
            cgroup: Redis Stream consumer group, required for reading
            cname : Redis Stream consumer name, required for reading
        '''
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD)

        # Init consumer group
        if cgroup and cname:
            try:
                self.redis.xgroup_create(REDIS_STREAM, cgroup, mkstream=True)
            except redis.exceptions.ResponseError as err:
                errmsg = str(err)
                if "BUSYGROUP" in errmsg:
                    pass
                else:
                    raise err
            self.cgroup = cgroup
            self.cname  = cname
    
    def add(self, event, is_json=True):
        data = json.dumps(event) if is_json else event
        self.redis.xadd(REDIS_STREAM, {REDIS_FIELD: data})

    def readgroup(self):
        ''' Read pending and new message.
            Return tuple of message (id, content)
        '''
        # '0'=Pending Entry List, '>'=New Entry
        for id in ('0', '>'):
            res = self.redis.xreadgroup(self.cgroup, self.cname, {REDIS_STREAM: id}, count=1, block=0)
            if res[0][1]:
                return (str(res[0][1][0][0], 'ascii'),
                        json.loads(res[0][1][0][1][REDIS_FIELD]))

    # ACK message
    def ack(self, id):
        res = self.redis.xack(REDIS_STREAM, self.cgroup, id)
        return res == 1
