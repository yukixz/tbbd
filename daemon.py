#!/usr/bin/env python3

import json
import logging
import signal
import sys
import time
import traceback
import importlib
from requests_oauthlib import OAuth1Session

import scripts


REQUESTS_OPTIONS = {
    'timeout': 60,
    # 'proxies': {
    #     'http': 'socks5://127.0.0.1:1080',
    #     'https': 'socks5://127.0.0.1:1080',
    # }
}


class TwitterStream():
    ''' Twitter stream implemented using streaming APIs.
        Provides all message types declared at:
        https://dev.twitter.com/streaming/overview/messages-types
    '''

    def __init__(self,
                 consumer_key, consumer_secret, access_token, access_secret):
        self.session = OAuth1Session(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_secret,
            )
        self.stream = None

    def create_stream(self):
        if not (self.stream is None or self.stream.raw.closed):
            logging.warning("Stream exists, shouldn't create again.")
            return
        logging.info("Creating stream.")
        URL = 'https://userstream.twitter.com/1.1/user.json'
        params = {"replies": "all"}
        response = self.session.get(URL, params=params,
                                    stream=True,
                                    **REQUESTS_OPTIONS)
        if response.status_code == 200:
            self.stream = response
        if response.status_code != 200:
            logging.critical("Failed to create stream: %s" % response.text)
            sys.exit(1)

    def close_stream(self):
        if self.stream is None:
            logging.warning("Stream not existed, cannot close.")
            return
        logging.info("Closing stream.")
        self.stream.close()
        self.stream = None

    def iter_messages(self):
        while True:
            self.create_stream()

            for line in self.stream.iter_lines(chunk_size=1):
                ''' Process Control Messages
                    Reconnect or disconnect if necessary
                    https://dev.twitter.com/streaming/overview/messages-types
                '''
                logging.debug(len(line))
                # Blank lines
                if len(line) == 0:
                    continue

                try:
                    message = json.loads(line.decode('UTF-8'))
                except ValueError:
                    logging.warning("Failed to load message: %s" % line)
                    continue

                # Disconnect messages (disconnect)
                if 'disconnect' in message:
                    logging.warning("Receive disconnect message: %s" % message)
                    if message['disconnect']['code'] == 12:
                        # reconnect
                        break
                    else:
                        # disconnect
                        sys.exit(1)

                # Stall warnings (warning)
                if 'warning' in message:
                    logging.warning("Warning messsage: %s" % message)
                    continue

                # Payload messages
                yield message

            self.close_stream()


class Daemon():
    def __init__(self, config_path):
        ''' :param config_path: Config file path, accepts json file only.
        '''
        signal.signal(signal.SIGINT, self.handle_SIGINT)
        # signal.signal(signal.SIGUSR1, self.handle_SIGUSR1)

        self.modules = {}
        self.scripts = {
            "any": [],
            "tweet": [],
            "delete": [],
            "scrub_geo": [],
            "friends": [],
            "favorite": [],
        }

        # Read config
        with open(config_path, 'r') as f:
            config_raw = f.read()
        config = json.loads(config_raw)

        # Init stream
        self.current_user = config['current_user']
        self.stream = TwitterStream(
            consumer_key=config['consumer_key'],
            consumer_secret=config['consumer_secret'],
            access_token=config['access_token'],
            access_secret=config['access_secret'],
            )

        # Init scripts
        modules = {}
        scripts = {}
        for type_ in self.scripts:
            scripts[type_] = []

        for name in config['scripts']:
            if name in self.modules:
                # Reload module when module was loaded
                try:
                    module = importlib.reload(self.modules[name])
                except ImportError as err:
                    logging.exception(err)
                    continue
            else:
                # Load module when module wasn't loaded
                try:
                    module = importlib.import_module("scripts.%s" % name)
                except ImportError as err:
                    logging.exception(err)
                    continue
            modules[name] = module

            for type_ in self.scripts:
                handler = getattr(module.handler, "do_%s" % type_, None)
                if callable(handler):
                    scripts[type_].append(handler)

        self.modules = modules
        self.scripts = scripts

    def process_message(self, message):
        ''' Guess message type and execute relevant scripts
            Docs: https://dev.twitter.com/streaming/overview/messages-types
            :param message:  a twitter message (json)
        '''
        # Any message
        if True:
            for script in self.scripts['any']:
                self.process_message_with_script(message, script)

        ''' Public stream messages
        '''
        # Standard Tweet payloads
        if 'id' in message:
            for script in self.scripts['tweet']:
                self.process_message_with_script(message, script)
        # Status deletion notices (delete)
        if 'delete' in message:
            for script in self.scripts['delete']:
                self.process_message_with_script(message, script)
        # Location deletion notices (scrub_geo)
        if 'scrub_geo' in message:
            for script in self.scripts['scrub_geo']:
                self.process_message_with_script(message, script)
        # Limit notices (limit)
        if 'limit' in message:
            pass
        # Withheld content notices (status_withheld, user_withheld)
        if 'status_withheld' in message:
            pass
        if 'user_withheld' in message:
            pass
        # Disconnect messages (disconnect)
            # Processed in self.skip_control_message()
        # Stall warnings (warning)
            # Processed in self.skip_control_message()
        if message.get('event') == "favorite":
            for script in self.scripts['favorite']:
                self.process_message_with_script(
                    message, script, current_user=self.current_user)

        ''' User stream messages
        '''
        # Friends lists (friends)
        if 'friends' in message:
            for script in self.scripts['friends']:
                self.process_message_with_script(message, script)
        # Direct Messages
            # TODO
        # Events (event)
        if 'event' in message:
            pass

    def process_message_with_script(self, message, script, *args, **kwargs):
        try:
            script(message, *args, **kwargs)
        except Exception as err:
            logging.warning("Script %s failed to process message:\n%s"
                            % (script.__func__, message))

    def run(self):
        while True:
            try:
                for message in self.stream.iter_messages():
                    self.process_message(message)
            except Exception as err:
                logging.error("Stream error")
                logging.debug(traceback.format_exc())
            finally:
                time.sleep(10)

    def handle_SIGINT(self, sig, frame):
        sys.exit(0)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        # stream=sys.stderr,
        filename="./daemon.log",
        format="%(asctime)s %(levelname)s %(funcName)s: %(message)s",
        )
    daemon = Daemon(config_path='./config.json')
    daemon.run()
