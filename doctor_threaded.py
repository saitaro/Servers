"""A script running the server which receives files from user, saves
them with a unique id (UUID) and sends them back by their id.
"""

import cgi
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from os import getcwd, makedirs, path
from socketserver import ThreadingTCPServer
from threading import Thread
from typing import Union
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

ADDRESS, PORT = 'localhost', 8000

DATABASE = 'db.sqlite'
FILEDIR = 'Uploads'


class HttpHandler(BaseHTTPRequestHandler):
    '''A tiny request handler for uploading and downloading files.'''

    def __init__(self: '__main__.HttpHandler', *args, **kwargs) -> None:
        '''
        The handler class constructor. Before initialization checks if
        the DATABASE file and the FILEDIR directory/folder both exist,
        otherwise creates them.
        '''
        makedirs(FILEDIR, exist_ok=True)

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

        super().__init__(*args, **kwargs)

    def read_from_db(self: '__main__.HttpHandler',
                     file_id: str) -> Union[tuple, None]:
        '''Fetch the file record from the database.'''
        try:
            conn = sqlite3.connect(DATABASE)
            with closing(conn):
                cursor = conn.cursor()
                query = f'''SELECT filepath, filename, extension, upload_date
                            FROM filepaths
                            WHERE uuid=:id;
                        '''
                cursor.execute(query, {'id': file_id})
                return cursor.fetchone()

        except sqlite3.DatabaseError as error:
            self.send_response(code=500)
            self.end_headers()
            self.wfile.write(bytes('Database error', 'utf-8'))
            print('Database error :', error)

    def send_file(self: '__main__.HttpHandler',
                  file_id: str,
                  filepath: str,
                  filename: str,
                  extension: str) -> None:
        '''Send the requested file to user.'''
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
            self.send_response(code=410)
            self.end_headers()
            self.wfile.write(bytes(f'File with id {file_id} was deleted.'),
                             'utf-8')

    def do_GET(self: '__main__.HttpHandler') -> None: # pylint: disable=C0103
        '''
        Check if a record for the given id exists in the DATABASE and
        send the respective response to user; if 'download' parameter
        provided, download the existing file to user from FILEPATH.
        Usage is as follows:

        CHECK
        http://<ADDRESS>:<PORT>/?id=<file_id>

        DOWNLOAD
        http://<ADDRESS>:<PORT>/?id=<file_id>&download=1
        '''
        print(111)
        get_query = urlsplit(self.path).query
        params = dict(parse_qsl(get_query))

        if 'id' not in params:
            print(222)
            self.send_response_only(code=200)
            self.end_headers()
            return

        file_id = params['id']

        db_response = self.read_from_db(file_id)

        if not db_response:
            print(333)
            self.send_response(code=204)
            self.end_headers()
            self.wfile.write(bytes(f'No files found with id {file_id}'),
                             'utf-8')
            return

        filepath, filename, extension, upload_date = db_response
        print(444)
        if 'download' not in params:
            print('THIS')
            self.send_response(code=200)
            self.end_headers()
            self.wfile.write(
                bytes(f'{filename}.{extension} was uploaded at {upload_date}',
                      'utf-8')
            )
        else:
            self.send_file(file_id, filepath, filename, extension)

    def do_POST(self: '__main__.HttpHandler') -> None: # pylint: disable=C0103
        '''
        Upload a file to FILEPATH and create the record for that
        in the DATABASE, then send it's id in the response message.
        Usage is as follows:

        UPLOAD
        POST request containing the file body to http://<ADDRESS>:<PORT>/
        Content-Length must be provided in the headers;
        If Content-Disposition is absent, the file will be saved as
        "filename.not_provided"
        '''
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length == 0:
            self.send_response(code=411)
            self.end_headers()
            return

        # content_disposition = self.headers.get('Content-Disposition',
        #                                        'name="filename.not_provided"')
        # filename, extension = re.findall(r'name="(.+)\.(\S+)"',
        #                                  content_disposition)[0]
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type']}
        )
        filename = form.list[0].filename
        extension = 'wooloo'
        print()
        print('filename', filename)
        print()

        file_content = self.rfile.read(content_length)
        uuid = str(uuid4())
        # filepath = path.join(getcwd(), FILEDIR, f'{uuid}.{extension}')
        filepath = path.join(getcwd(), FILEDIR, f'{filename}')

        with open(filepath, 'wb') as file:
            file.write(file_content)

        try:
            with sqlite3.connect(DATABASE) as conn:
                query = '''INSERT INTO filepaths VALUES (
                               :uuid,
                               :filepath,
                               :filename,
                               :extension,
                               :upload_date
                           );'''
                conn.execute(query, {'uuid': uuid,
                                     'filepath': filepath,
                                     'filename': filename,
                                     'extension': extension,
                                     'upload_date': datetime.now()})
            conn.close()

            self.send_response(code=201)
            self.end_headers()
            self.wfile.write(bytes(uuid, 'utf-8'))

        except sqlite3.DatabaseError as error:
            self.send_response(code=500)
            self.end_headers()
            self.wfile.write(bytes('Database error', 'utf-8'))
            print('Database error :', error)


if __name__ == "__main__":
    with ThreadingTCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving on port', PORT)
        SERVER_THREAD = Thread(httpd.serve_forever(), daemon=True)
        SERVER_THREAD.start()
