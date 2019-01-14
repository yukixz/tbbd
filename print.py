#!/usr/bin/env python3

import json
import uuid
import redis
from utils import Queue

queue = Queue("print", "print1")

while True:
    id, evt = queue.readgroup()
    print('=' * 80)
    print(id)
    print(json.dumps(evt, indent=4, ensure_ascii=False))
    print('=' * 80)
    queue.ack(id)
