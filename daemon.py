#!/usr/bin/env python3

import json
import logging
import signal
import sys
import importlib
from requests_oauthlib import OAuth1Session

import scripts


class Daemon():
    def __init__(self, config_path):
        self.session = None
        self.stream = None
        self.modules = {}
        self.scripts = {
            "any": [],
            "tweet": [],
            "delete": [],
            "scrub_geo": [],
            "friends": [],
        }
        logging.basicConfig(
            level=logging.DEBUG,
            filename="./daemon.log",
            format="%(asctime)s %(levelname)s %(funcName)s: %(message)s",
            )

        self.reload(config_path=config_path)
        signal.signal(signal.SIGINT, self.handle_SIGINT)
        # signal.signal(signal.SIGUSR1, self.handle_SIGUSR1)

    def __del__(self):
        pass

    def reload(self, config_path="./config.json"):
        ''' Reload configuration
            :param config_path: Config file path, accept json file only.
        '''
        logging.info("Reload configuration")

        # Read config
        with open(config_path, 'r') as f:
            config_raw = f.read()
        config = json.loads(config_raw)

        # Init twitter session
        ''' We should not allow update twitter session on running.
        '''
        if self.session is None:
            self.session = OAuth1Session(
                client_key=config['consumer_key'],
                client_secret=config['consumer_secret'],
                resource_owner_key=config['access_token'],
                resource_owner_secret=config['access_secret'],
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
                    logging.error(err)
                    continue
            else:
                # Load module when module wasn't loaded
                try:
                    module = importlib.import_module("scripts.%s" % name)
                except ImportError as err:
                    logging.error(err)
                    continue
            modules[name] = module

            for type_ in self.scripts:
                handler = getattr(module.handler, "do_%s" % type_, None)
                if callable(handler):
                    scripts[type_].append(handler)

        self.modules = modules
        self.scripts = scripts

    def create_stream(self):
        if self.stream is not None:
            logging.warning("Stream was created. Mustn't create again.")
            return
        URL = 'https://userstream.twitter.com/1.1/user.json'
        response = self.session.get(URL, stream=True)
        if response.status_code == 200:
            self.stream = response
        if response.status_code != 200:
            logging.critical("Failed to create stream: %s" % response.text)
            sys.exit(1)

    def close_stream(self):
        if self.stream is None:
            logging.warning("Stream unavailable, cannot close.")
            return
        self.stream.close()
        self.stream = None

    def skip_control_message(self, message):
        ''' Check message and skip control message
            Docs: https://dev.twitter.com/streaming/overview/messages-types
            :param message: a twitter message (json)
            :return None: if message is processed.
            :return message: else
        '''
        # Blank lines
        if len(message) == 0:
            return None
        # Disconnect messages (disconnect)
        if 'disconnect' in message:
            if message['disconnect']['code'] == 12:
                # reconnect
                return None
            else:
                # disconnect
                sys.exit(1)
                return None
        # Stall warnings (warning)
        if 'warning' in message:
            logging.warning("Warning messsage: %s" % message)
            return None
        # `message` is not a control message
        return message

    def process_message(self, message):
        ''' Guess message type and execute relevant scripts
            Docs: https://dev.twitter.com/streaming/overview/messages-types
            :param message:  a twitter message (json)
        '''
        # Any message
        if True:
            for script in self.scripts.get('any', []):
                script(message)

        ''' Public stream messages
        '''
        # Standard Tweet payloads
        if 'id' in message:
            for script in self.scripts.get('tweet', []):
                script(message)
        # Status deletion notices (delete)
        if 'delete' in message:
            for script in self.scripts.get('delete', []):
                script(message)
        # Location deletion notices (scrub_geo)
        if 'scrub_geo' in message:
            for script in self.scripts.get('scrub_geo', []):
                script(message)
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

        ''' User stream messages
        '''
        # Friends lists (friends)
        if 'friends' in message:
            for script in self.scripts.get('friends', []):
                script(message)
        # Direct Messages
            # TODO
        # Events (event)
        if 'event' in message:
            pass

    def run(self):
        self.create_stream()
        for line in self.stream.iter_lines(chunk_size=1):
            if len(line) == 0:
                continue
            try:
                message = json.loads(line.decode('UTF-8'))
                if self.skip_control_message(message) is not None:
                    self.process_message(message)
            except Exception as err:
                logging.warning(
                    "Failed to process message: %s\n%s" % (err, line))

    def handle_SIGINT(self, sig, frame):
        sys.exit(0)

    def handle_SIGUSR1(self, sig, frame):
        self.reload()


if __name__ == '__main__':
    daemon = Daemon(config_path='./config.json')
    daemon.run()
