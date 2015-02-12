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
        self.modules = {}
        self.scripts = {
            "tweet": [],
        }
        logging.basicConfig(level=logging.DEBUG,
                            filename="./daemon.log",
                            format="%(asctime)s %(levelname)s %(funcName)s: %(message)s",)

        self.reload(config_path=config_path)
        signal.signal(signal.SIGINT, self.handle_SIGINT)
        signal.signal(signal.SIGUSR1, self.handle_SIGUSR1)

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
        self.session = OAuth1Session(client_key=config['consumer_key'],
                                     client_secret=config['consumer_secret'],
                                     resource_owner_key=config['access_token'],
                                     resource_owner_secret=config['access_secret'])

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

    def run(self):
        r = self.session.get('https://userstream.twitter.com/1.1/user.json',
                             stream=True)
        for line in r.iter_lines(chunk_size=1):
            if len(line) == 0:
                continue
            try:
                message = json.loads(line.decode('UTF-8'))
                for script in self.scripts["tweet"]:
                    script(message)
            except:
                logging.warning("Failed to process json object: %s" % line)

    def handle_SIGINT(self, sig, frame):
        sys.exit(0)

    def handle_SIGUSR1(self, sig, frame):
        self.reload()


if __name__ == '__main__':
    daemon = Daemon(config_path='./config.json')
    daemon.run()
