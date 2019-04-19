"""A script running the server which receives files from user, saves
them with a unique id (UUID) and sends them back by their id.
"""

import cgi
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from os import getcwd, makedirs, path
from socketserver import ThreadingTCPServer
from threading import Thread
from typing import Union
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4


ADDRESS, PORT = '127.0.0.1', 8000

DATABASE = 'db.sqlite'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILEDIR = os.path.join(BASE_DIR, 'uploads')


class HttpHandler(BaseHTTPRequestHandler):
    '''A tiny request handler for uploading and downloading files.'''

    def __init__(self, *args, **kwargs) -> None:
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

    def read_from_db(self, file_id: str) -> Union[tuple, None]:
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
            self.send_response(code=500, message='Database error')
            self.end_headers()
            print('Database error :', error)

    def send_file(self,
                  file_id: str,
                  filepath: str,
                  filename: str,
                  extension: str) -> None:
        """Send the requested file to user."""
        try:
            with open(filepath, 'rb') as file:
                self.send_response(code=200)
                self.send_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}.{extension}"'
                )
                self.end_headers()
                downloading_content = file.read()
                self.wfile.write(downloading_content)

        except FileNotFoundError:
            self.send_response(code=410,
                               message=f'File with id {file_id} was deleted')
            self.end_headers()

    def do_GET(self) -> None:  # pylint: disable=C0103
        """
        Check if a record for the given id exists in the DATABASE and
        send the respective response to user; if 'download' parameter
        provided, download the existing file to user from FILEPATH.
        Usage is as follows:

        CHECK
        http://<ADDRESS>:<PORT>/?id=<file_id>

        DOWNLOAD
        http://<ADDRESS>:<PORT>/?id=<file_id>&download=1
        """
        get_query = urlsplit(self.path).query
        params = dict(parse_qsl(get_query))

        if 'id' not in params:
            self.send_response_only(code=200)
            self.end_headers()
            return

        file_id = params['id']

        db_response = self.read_from_db(file_id)

        if not db_response:
            self.send_response(code=204,
                               message=f'No database record for id {file_id}')
            self.end_headers()
            return

        filepath, filename, extension, upload_date = db_response

        if 'download' not in params:
            self.send_response(code=200)
            self.end_headers()
            self.wfile.write(
                bytes(f'{filename} was uploaded at {upload_date}', 'utf-8'))
        else:
            self.send_file(file_id, filepath, filename, extension)

    def do_POST(self) -> None:  # pylint: disable=C0103
        """
        Upload a file to FILEPATH and create the record for that
        in the DATABASE, then send it's id in the response message.
        Usage is as follows:

        UPLOAD
        POST request containing the file body to http://<ADDRESS>:<PORT>/

        Files are saved as <uuid>.<extension> to prevent name duplication.
        """
        uuid = str(uuid4())
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type']}
        )
        filename = form.list[0].filename
        # extension = re.findall(r'.+\.(\S+)', filename)[0]
        filepath = os.path.join(FILEDIR, filename)

        with open(filepath, 'wb') as file:
            try:
                uploading_content = form.list[0].file.read()
                file.write(uploading_content)
            except TypeError:
                self.send_response(code=400)
                self.end_headers()
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
                                     'extension': '',
                                     'upload_date': datetime.now()})
            conn.close()

            self.send_response(code=201)
            self.end_headers()
            self.wfile.write(bytes(uuid, 'utf-8'))

        except sqlite3.DatabaseError as error:
            self.send_response(code=500, message='Database error')
            self.end_headers()
            print('Database error :', error)


if __name__ == "__main__":
    try:
        PORT = int(sys.argv[1])
    except IndexError:
        pass
    with ThreadingTCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving on port', PORT)
        SERVER_THREAD = Thread(httpd.serve_forever(), daemon=True)
        SERVER_THREAD.start()
