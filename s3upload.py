import boto3
import botocore
import threading
import os
import os.path
import sys
import visit_core
import util
import math
import traceback
import humanize

def get_bucket_name():
    return 'pybak-2018-07-14'

class Progress(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(util.get_file_length(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self.lastPercentage = 0

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = math.floor((self._seen_so_far / self._size) * 100)
            if percentage - self.lastPercentage > 10:
                data = (percentage, humanize.naturalsize(self._seen_so_far), humanize.naturalsize(self._size), self._filename)
                visit_core.log("%.2f%% (%s / %s) %s\n" % data, 's3++')
                self.lastPercentage = percentage

class S3Upload(object):
    def __init__(self, bucket_name):
        visit_core.log('[s3u.init] bucket_name=\'%s\'\n' % bucket_name)
        self.s3 = boto3.resource('s3')
        self.bucket_name = bucket_name

    def exists(self, key):
        try:
            self.s3.Object(self.bucket_name, key).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else:
                visit_core.log_error('[s3u.exists] exception %s\n' % str(e))
                raise e
        except Exception as e:
            return False
        return True

    def upload(self, src, key):
        visit_core.log('[s3u.upload] src=\'%s\' key=\'%s\'\n' % (src, key))
        self.s3.meta.client.upload_file(
            src,
            self.bucket_name,
            key,
            Callback=Progress(src)
        )

if __name__ == '__main__':
    s3u = S3Upload(get_bucket_name())
    s3u.upload('client.py', 'client.py')
    
