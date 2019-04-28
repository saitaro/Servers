"""Test module for doctor_threaded.py server script."""

import unittest
import subprocess
import filecmp
import sqlite3
from os import path, remove
from urllib.request import urlopen, urlretrieve
from urllib.parse import urlencode

import requests

from doctor_threaded import BASE_DIR, FILEDIR, DATABASE


class GeneralTestCase(unittest.TestCase):
    """Basic checks without files manipulation."""

    @classmethod
    def setUpClass(cls):
        cls.HOST = '127.0.0.1'
        cls.PORT = 8000
        cls.server_url = f'http://{cls.HOST}:{cls.PORT}/'
        cls.server = subprocess.Popen(f'python doctor_threaded.py {cls.PORT}')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()

    def test_server_responding(self):
        '''Check the server responds to a get request.'''
        response = urlopen(self.server_url)
        self.assertEqual(response.status, 200)

    def test_wrong_file_id_response(self):
        '''Check the request with a made-up file id
        reveives a "No record for id" message'''
        wrong_id = 'wrong-id-0e18-4f06-8349-7cbf3155890d'
        params = urlencode({'id': wrong_id})
        bad_response = urlopen(self.server_url + '?' + params)

        self.assertEqual(bad_response.status, 204)
        self.assertEqual(bad_response.reason,
                         f'No database record for id {wrong_id}')


class FileHandlingTestCase(unittest.TestCase):
    '''File manipulations checks.'''

    @classmethod
    def setUpClass(cls):
        cls.HOST = '127.0.0.1'
        cls.PORT = 8000
        cls.server = subprocess.Popen(f'python doctor_threaded.py {cls.PORT}')
        cls.server_url = f'http://{cls.HOST}:{cls.PORT}/'
        cls.sample_file = path.join(BASE_DIR, 'sample_file.txt')
        with open(cls.sample_file, 'w') as file:
            file.write('Hello, world!')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        remove(cls.sample_file)

    def test_file_operations(self):
        """Check the server's ability to receive and return files."""
        with open(self.sample_file, 'rb') as file:
            response = requests.post(
                self.server_url,
                files={'name': file}
            )
        self.assertEqual(response.status_code, 201)
        uuid = response.text

        # Uploaded file is the same as the local one
        _, extension = path.splitext(self.sample_file)
        filecmp.clear_cache()
        self.assertTrue(filecmp.cmp(self.sample_file,
                                    path.join(FILEDIR, f'{uuid}{extension}')))

        # Server responses with the proper filename
        check_response = urlopen(self.server_url + '?id=' + uuid)
        self.assertEqual(check_response.read().decode(),
                         path.basename(self.sample_file))

        # Downloaded file is the same as the previously uploaded
        download, _ = urlretrieve(
            self.server_url + '?id=' + uuid + '&download=1',
            path.join(BASE_DIR, 'download')
        )
        self.assertTrue(filecmp.cmp(download, self.sample_file))

        remove(download)
        remove(path.join(FILEDIR, f'{uuid}{extension}'))

        with sqlite3.connect(DATABASE) as conn:
            query = '''DELETE FROM filepaths
                       WHERE uuid = :uuid
                    '''
            conn.execute(query, {'uuid': uuid})
        conn.close()


if __name__ == '__main__':
    unittest.main()
