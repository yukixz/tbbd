#!/usr/bin/env python3

import logging
import os
import os.path
import sqlite3
import subprocess


class ImageDownloadHandler():
    FOLDER = "./images/"
    DATABASE = os.path.join(FOLDER, "manifest.db")

    def __init__(self):
        # Create download folder if not exists or
        # Try to delete if exist but not a diirectory
        if os.path.exists(self.FOLDER) and not os.path.isdir(self.FOLDER):
            try:
                os.remove(self.FOLDER)
            except Exception as e:
                logging.critical(e)
                raise e
        if not os.path.exists(self.FOLDER):
            os.mkdir(self.FOLDER)

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
            logging.info("")
            cursor = self.connection.cursor()
            cursor.execute((
                "CREATE TABLE manifest ("
                "   tweet_url VARCHAR(255),"
                "   media_url VARCHAR(255),"
                "   owner UNSIGNED BIGINT"
                ")"
                ))

    def __del__(self):
        self.connection.commit()
        self.connection.close()

    def download(self, image, user):
        # print("Download image: %s" % image.url)

        # Save image info into datebase
        cursor = self.connection.cursor()
        cursor.execute((
                "INSERT INTO manifest"
                "(tweet_url, media_url, owner)"
                "VALUES (?,?,?)"
            ), (
                image['expanded_url'],
                image['media_url'],
                user['id']
            ))

        # Retrive the image
        subfolder = "@{screen_name}-{id}".format(**user)
        filename = os.path.basename(image['media_url'])
        path = os.path.join(self.FOLDER, filename)
        url = image['media_url'] + ':orig'
        subprocess.Popen([
            "wget", url,
            "-O%s" % path,
            "--no-use-server-timestamps",
            "--quiet",
            ])

    def do_tweet(self, tweet):
        # Skip retweet
        if 'retweeted_status' in tweet:
            return
        if 'RT @' in tweet['text']:
            return

        entities = tweet.get('extended_entities', {}).get('media', [])
        user = tweet['user']
        for media in entities:
            if media['type'] == 'photo':
                self.download(media, user)


handler = ImageDownloadHandler()

if __name__ == '__main__':
    handler = ImageDownloadHandler()
    handler.do_tweet(
        {
            "text": "http://t.co/bF5uDpdZvU",
            "user": {
                "id": 327877263,
                "screen_name": "MikaAkagi",
                },
            "extended_entities": {
                "media": [{
                    "expanded_url":
                        "http://twitter.com/MikaAkagi/status/567365717209513984/photo/1",
                    "media_url": "http://pbs.twimg.com/media/B9-wHL4CYAE7t1J.jpg",
                    "type": "photo",
                }]
            },
        }
        )
