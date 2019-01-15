#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import hashlib
import hmac
import json
import logging
import redis
import sys
from datetime import datetime
from flask import Flask, abort, request
from config import TWITTER_CONSUMER_SECRET
from utils import Queue

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s - %(message)s",
)

app = Flask(__name__)
queue = Queue()


@app.after_request
def track_request(response):
    logging.debug("Payload\n" + json.dumps({
        "time"   : str(datetime.now()),
        "request": {
            "endpoint"   : request.endpoint,
            "method"     : request.method,
            "path"       : request.path,
            "headers"    : dict(request.headers),
            "args"       : dict(request.args),
            "form"       : request.form,
            "data"       : str(request.data, 'ascii'),
            "remote_addr": request.remote_addr,
        },
        "response": {
            "status_code": response.status_code,
            "headers"    : dict(response.headers),
            "data"       : str(response.data, 'ascii'),
        },
    }, indent=4))
    return response


# Challenge-Response Checks
@app.route("/webhook", methods=['GET'])
def webhook_crc():
    if 'crc_token' not in request.args:
        abort(400)
    token = request.args['crc_token']
    digest = hmac.new(
        key=TWITTER_CONSUMER_SECRET.encode(),
        msg=token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    response_token = base64.b64encode(digest).decode()
    logging.info(f"CRC: token={token}, response_token={response_token}")
    return json.dumps({
        'response_token': "sha256=" + response_token,
    })


# Events Webhook
@app.route("/webhook", methods=['POST'])
def webhook_event():
    # Validate Request from Twitter
    signature_user = request.headers.get('x-twitter-webhooks-signature', "")
    if signature_user.startswith("sha256="):
        signature_user = signature_user[7:]
    digest = hmac.new(
        key=TWITTER_CONSUMER_SECRET.encode(),
        msg=request.data,
        digestmod=hashlib.sha256,
    ).digest()
    signature_server = base64.b64encode(digest).decode()
    if not hmac.compare_digest(signature_user, signature_server):
        logging.warn(f"Webhook signature invalid: signature_user={signature_user}, signature_server={signature_server}")
        return abort(400)

    # Add Event Message to Redis Queue
    if request.json:
        queue.add(request.json)
    else:
        logging.warn(f"Non-JSON message: {request.data}")

    return "OK"


if __name__ == '__main__':
    app.run()
