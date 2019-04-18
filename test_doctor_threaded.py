from unittest import main, TestCase
import io
import subprocess
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from time import sleep
from os import path, getcwd, remove
from time import sleep
import requests
import http.client


# class CheckTestCase(TestCase):

#     @classmethod
#     def setUpClass(cls):
#         cls.PORT = 8080
#         cls.server_url = f'http://127.0.0.1:{cls.PORT}/'
#         cls.server = subprocess.Popen(f'python doctor_threaded.py {cls.PORT}')

#     @classmethod
#     def tearDownClass(cls):
#         cls.server.terminate()
#         # sleep(1)

#     def test_server_responding(self):
#         response = urlopen(self.server_url)
#         self.assertEqual(response.status, 200)

#     def test_wrong_file_id_response(self):
#         wrong_id = 'wrong-id-0e18-4f06-8349-7cbf3155890d'
#         params = urlencode({'id': wrong_id})
#         bad_response = urlopen(self.server_url + '?' + params)

#         self.assertEqual(bad_response.status, 204)
#         self.assertEqual(bad_response.reason,
#                          f'No database record for id {wrong_id}')


class UploadTestCase(TestCase):

    def setUp(self):
        self.PORT = 8000
        self.server = subprocess.Popen(f'python doctor_threaded.py {self.PORT}')
        self.server_url = f'http://127.0.0.1:{self.PORT}/'

        sleep(2)

    def tearDown(self):
        self.server.terminate()

    def test_upload_file(self):
        # sample_file = path.join(getcwd(), 'sample_file.txt')
        # with open(sample_file, 'w') as file:
        #     file.write('Hello, world!')

        with open('012 Non-Repeating Character (Difficulty = __).mp4', 'rb') as file:
            files = {'file': file}
            headers = {
                'Content-Type': 'text/plain',
                'Content-Disposition': 'attachment; filename="sample_file.txt"'
            }
            print(requests.post(self.server_url,
                                # files=files,
                                headers=headers).status_code)
        # request  = Request(self.server_url, 
        #                    data=open('012 Non-Repeating Character (Difficulty = __).mp4', 'rb'), 
        #                    headers={'Content-Type': 'video/mpeg'})
        # print(requests.get(self.server_url).status_code)
        # response = urlopen(request).read().decode()
        # sample_file.close()
        # remove('sample_file.txt')



    # def test_check_uploaded_file(self):
        
# class DownloadTestCase(TestCase):
    
#     def test_download_file(self):
#         pass


if __name__ == '__main__':
    main()
