from unittest import main, TestCase
import subprocess
import socket
from datetime import datetime
from time import sleep
import requests
import os
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from os import path, getcwd, remove
import filecmp

from doctor_threaded import BASE_DIR, FILEDIR

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# FILEDIR = os.path.join(BASE_DIR, 'Uploads')

class GeneralTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.PORT = 8000
        cls.server_url = f'http://127.0.0.1:{cls.PORT}/'
        cls.server = subprocess.Popen(f'python doctor_threaded.py {cls.PORT}')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        # sleep(1)

    def test_server_responding(self):
        response = urlopen(self.server_url)
        self.assertEqual(response.status, 200)

    def test_wrong_file_id_response(self):
        wrong_id = 'wrong-id-0e18-4f06-8349-7cbf3155890d'
        params = urlencode({'id': wrong_id})
        bad_response = urlopen(self.server_url + '?' + params)

        self.assertEqual(bad_response.status, 204)
        self.assertEqual(bad_response.reason,
                         f'No database record for id {wrong_id}')

class UploadTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.PORT = 5000
        cls.server = subprocess.Popen(f'python doctor_threaded.py {cls.PORT}', shell=True)
        cls.server_url = f'http://127.0.0.1:{cls.PORT}/'
        cls.sample_file = path.join(BASE_DIR, 'sample_file.txt')
        with open(cls.sample_file, 'w') as file:
            file.write('Hello, world!')
        # cls.sample_file = os.path.join(BASE_DIR, 'git.pdf')
        # cls.sample_file = os.path.join(BASE_DIR, '012 Non-Repeating Character (Difficulty = __).mp4')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()

    def test_upload_file(self):
        with open(self.sample_file, 'rb') as file:
            files = {'name': file}
            response = requests.post(
                self.server_url,
                files=files
            )

        self.assertEqual(response.status_code, 201)
        uuid = response.text

        # Uploaded file is the same as the local one
        _, extension = path.splitext(self.sample_file)
        filecmp.clear_cache()
        self.assertTrue(filecmp.cmp(self.sample_file,
                                    path.join(FILEDIR, f'{uuid}{extension}')))

        # Server responses with the proper filename
        check_response = requests.get(self.server_url +'?id='+ uuid)
        self.assertEqual(
            check_response.text,
            path.basename(self.sample_file))
        
    def test_download_file(self):
        pass

# class DownloadTestCase(TestCase):
    
#     def test_download_file(self):
#         pass


if __name__ == '__main__':
    main()
