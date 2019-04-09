from unittest import main, TestCase
from subprocess import Popen
import http.client, urllib.parse
from time import sleep


class UploadTestCase(TestCase):
    def setUp(self):
        self.server = Popen('doctor_sync.py', shell=True)
        self.conn = http.client.HTTPConnection('127.0.0.1')
        sleep(2)

        print(self.server)
        print(dir(self.server))

    def tearDown(self):
        self.server.kill()

    def test_file_upload(self):
        # conn.request('GET', '', params, headers)
        self.conn.request('GET', '127.0.0.1', 5050)
        response = conn.getresponse()
        print(response.status, response.reason)



class DownloadTestCase(TestCase):
    pass


if __name__ == '__main__':
    main()