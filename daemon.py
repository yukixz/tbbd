#!/usr/bin/env python3

import json
import signal
import sys
import importlib
from requests_oauthlib import OAuth1Session

import scripts


class TwitterStreamingDaemon():
    def __init__(self, config_path):
        self.session = None
        self.modules = {}
        self.scripts = {
            "tweet": [],
        }

        self.reload(config_path=config_path)
        signal.signal(signal.SIGINT, self.handle_SIGINT)
        signal.signal(signal.SIGUSR1, self.handle_SIGUSR1)

    def __del__(self):
        pass

    def reload(self, config_path="./config.json"):
        ''' Reload configuration
            :param config_path: Config file path, accept json file only.
        '''
        #logging.log()
        # Read config
        with open(config_path, 'r') as f:
            config_raw = f.read()
        config = json.loads(config_raw)

        # Init twitter session
        self.session = OAuth1Session(client_key=config['consumer_key'],
                                     client_secret=config['consumer_secret'],
                                     resource_owner_key=config['access_token'],
                                     resource_owner_secret=config['access_secret'])

        # Reload scripts
        modules = {}
        scripts = {}
        for hook in self.scripts:
            scripts[hook] = []

        for name in config['scripts']:
            if name in self.modules:
                # Reload module when module was loaded
                try:
                    module = importlib.reload(self.modules[name])
                except Exception as err:
                    # logging.error()
                    raise err
            else:
                # Load module when module wasn't loaded
                try:
                    module = importlib.import_module("scripts.%s" % name)
                except ImportError:
                    # logging.error()
                    continue
            modules[name] = module

            for hook, script in module.HOOKS.items():
                if hook in scripts:
                    scripts[hook].append(script)

        self.modules = modules
        self.scripts = scripts

    def run(self):
        ''' Run the streaming client_secret
        '''
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
                print(line)

    def handle_SIGINT(self, sig, frame):
        sys.exit(0)

    def handle_SIGUSR1(self, sig, frame):
        self.reload()


if __name__ == '__main__':
    daemon = TwitterStreamingDaemon(config_path='./config.json')
    daemon.run()
