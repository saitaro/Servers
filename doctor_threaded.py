import socketserver
import sqlite3
import re
from threading import Thread
from datetime import datetime
from os import getcwd, path, mkdir
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qsl
from contextlib import closing
from uuid import uuid4


ADDRESS, PORT = '127.0.0.1', 5050

DATABASE = 'db.sqlite'
FILEDIR = 'Uploads'

    
class HttpHandler(BaseHTTPRequestHandler):
    "A tiny request handler for uploading and downloading files."

    def __init__(self, *args, **kwargs):
        prep_worker = Thread(target=self.prepare)
        prep_worker.start()
        prep_worker.join()

        super().__init__(*args, **kwargs)

    def prepare(self):
        if not path.isdir(FILEDIR):
            mkdir(FILEDIR)

        if not path.isfile(DATABASE):
            conn = sqlite3.connect(DATABASE)
            with conn:
                conn.execute('''CREATE TABLE filepaths (
                                    uuid CHARACTER(36) PRIMARY KEY,
                                    filepath TEXT NOT NULL,
                                    filename TEXT NOT NULL,
                                    extension TEXT,
                                    upload_date TEXT
                                );''')
            conn.close()
            print(f'Database {DATABASE} created')
            
    def do_GET(self):
        '''
        Check if a record for the given id exists in the DATABASE and
        send the respective response to user; if 'download' parameter 
        provided, download the existing file to user from FILEPATH.
        '''
        get_query = urlsplit(self.path).query
        params = dict(parse_qsl(get_query))

        if 'id' not in params:
            self.send_response_only(code=200)
            self.end_headers()
            return

        download = 'download' in params

        response_worker = Thread(target=self.data_response, 
                                 args=(params['id'], download))
        response_worker.start()
        response_worker.join()

    def data_response(self, file_id, download):
        try:
            with closing(sqlite3.connect(DATABASE)) as conn:
                cursor = conn.cursor()
                query = f'''SELECT filepath, filename, extension, upload_date
                            FROM filepaths
                            WHERE uuid=:id;
                        '''
                cursor.execute(query, {'id': file_id})
                db_response = cursor.fetchone()

        except sqlite3.DatabaseError as e:
            self.send_response(code=500, message='Database error')
            self.end_headers()
            print('Database error :', e)
            return

        if db_response:
            filepath, filename, extension, upload_date = db_response

            if download:
                try:
                    with open(filepath, 'rb') as file:
                        self.send_response(code=200)
                        self.send_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}.{extension}"'
                        )
                        self.end_headers()
                        data = file.read()
                        self.wfile.write(data)

                except FileNotFoundError:
                    self.send_response(
                        code=404,
                        message=f'File with id {file_id} was deleted.'
                    )
                    self.end_headers()
            else:
                self.send_response(
                    code=200,
                    message=f'{filename}.{extension} uploaded at {upload_date}'
                )
                self.end_headers()
        else:
            self.send_response(code=404, 
                               message=f'No files found with id {file_id}')
            self.end_headers()
    
    def do_POST(self):
        '''
        Upload a file to FILEPATH and create the record for that
        in the DATABASE, then send it's id in the response message.
        '''
        if not self.headers.get('Content-Length'):
            self.send_response(code=411, message='Length required')
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])

        if content_length == 0:
            self.send_response(code=400, message='No file provided')
            self.end_headers()
            return

        file_header = self.headers['Content-Disposition']
        filename, extension = re.findall(r'name="(.+)\.(\S+)"', file_header)[0]
        uuid = uuid4()
        filepath = path.join(getcwd(), FILEDIR, f'{uuid}.{extension}')

        file_worker = Thread(target=self.write_file, 
                             args=(filepath, content_length),
                             daemon=True)

        db_worker = Thread(target=self.write_to_db, 
                           args=(uuid, filepath, filename, extension),
                           daemon=True)

        file_worker.start(), db_worker.start()

        db_worker.join()
        self.end_headers()

    def write_file(self, filepath, content_length):
        content = self.rfile.read(content_length)
        with open(filepath, 'wb') as file:
            file.write(content)

    def write_to_db(self, uuid, filepath, filename, extension):       
        try:
            with sqlite3.connect(DATABASE) as conn:
                query = '''INSERT INTO filepaths VALUES (
                            :uuid,
                            :filepath,
                            :filename,
                            :extension,
                            :upload_date
                        );'''
                conn.execute(query, {'uuid': str(uuid), 
                                    'filepath': filepath,
                                    'filename': filename,
                                    'extension': extension,
                                    'upload_date': datetime.now()})
            conn.close()
            self.send_response(code=201, message=f'File saved with id {uuid}')

        except sqlite3.DatabaseError as e:
            self.send_response(code=500, message='Database error')
            print('Database error :', e)


if __name__ == "__main__":
    with socketserver.TCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving at port', PORT)
        httpd.serve_forever()
