#!/usr/bin/env python3

import logging
import os
import os.path
import sqlite3
import subprocess


class Image():
    def __init__(self, url, owner, tweet):
        ''' :param url: url of a image
            :param owner: owner's id if the image
            :parem tweet: tweet's id contains the image
        '''
        self.url = url
        self.owner = owner
        self.tweet = tweet


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
            cursor.execute(
                '''
CREATE TABLE manifest (
    url VARCHAR(255),
    owner UNSIGNED BIGINT,
    tweet UNSIGNED BIGINT
)
                ''')

    def __del__(self):
        self.connection.commit()
        self.connection.close()

    def download(self, image):
        # print("Download image: %s" % image.url)

        # Save image info into datebase
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO manifest (url, owner, tweet) VALUES (?,?,?)",
            (image.url, image.owner, image.tweet))

        # Retrive the image
        url = image.url + ':orig'
        filename = os.path.basename(image.url)
        path = os.path.join(self.FOLDER, filename)
        subprocess.Popen([
            "wget", url,
            "-O%s" % path,
            ])

    def do_tweet(self, tweet):
        # Skip retweet
        if 'retweeted_status' in tweet:
            return
        
        images = tweet.get('extended_entities', {}).get('media', [])
        for image in images:
            self.download(Image(
                url=image['media_url'],
                owner=tweet['user']['id'],
                tweet=tweet['id'],
                ))


handler = ImageDownloadHandler()

if __name__ == '__main__':
    handler = ImageDownloadHandler()
    handler.download(Image(
            url="http://pbs.twimg.com/media/B9-wHL4CYAE7t1J.jpg",
            owner=327877263,
            tweet=567365717209513984,
        ))
