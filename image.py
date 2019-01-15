#!/usr/bin/env python3

import logging
import os
import sqlite3
import subprocess
from time import sleep
from utils import Queue

SKIP_USERS = (153642121, )

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s - %(message)s",
)

class ImageDownloader():
    DATAROOT = "./image/"
    DATABASE = os.path.join(DATAROOT, "manifest.db")

    def __init__(self):
        if not os.path.exists(self.DATAROOT):
            os.mkdir(self.DATAROOT)

        # Init Queue
        self.queue = Queue("image", "image1")

        # Establish database connection
        self.connection = sqlite3.connect(
            self.DATABASE,
            isolation_level=None
            )
        # Create table if not exist
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM manifest limit 1")
        except sqlite3.OperationalError:
            cursor = self.connection.cursor()
            cursor.execute((
                "CREATE TABLE manifest ("
                "   user  UNSIGNED BIGINT,"
                "   name  VARCHAR(255),"
                "   tweet UNSIGNED BIGINT,"
                "   text  VARCHAR(255),"
                "   media VARCHAR(255)"
                ")"
                ))

    def __del__(self):
        self.connection.commit()
        self.connection.close()

    def download(self, tweet, media):
        user = tweet['user']
        logging.info(f"Download @{user['screen_name']} {tweet['id']}")

        # Save image info into datebase
        cursor = self.connection.cursor()
        cursor.execute((
                "INSERT INTO manifest"
                "(user, name, tweet, text, media)"
                "VALUES (?,?,?,?,?)"
            ), (
                user['id'], user['screen_name'],
                tweet['id'], tweet['text'],
                media['media_url'],
            ))

        # Retrive the image
        subfolder = os.path.join(self.DATAROOT, "@{screen_name}-{id}".format(**user))
        if not os.path.exists(subfolder):
            os.mkdir(subfolder)
        filename = os.path.basename(media['media_url'])
        path = os.path.join(subfolder, filename)
        url = media['media_url'] + ':orig'
        subprocess.Popen([
            "wget", url,
            "-O%s" % path,
            "--no-use-server-timestamps",
            "--quiet",
            ])
    
    def process_message(self, message):
        for event in message.get("favorite_events", []):
            tweet = event["favorited_status"]
            entities = tweet.get('extended_entities', {}).get('media', [])
            for media in entities:
                if media['type'] == 'photo':
                    self.download(tweet, media)
        return True
    
    def run(self):
        while True:
            try:
                id, message = self.queue.readgroup()
                if self.process_message(message):
                    self.queue.ack(id)
                sleep(1)
            except Exception:
                logging.exception(f"Error in process_message")

if __name__ == '__main__':
    app = ImageDownloader()
    app.run()
