"""A script running the server which receives files from user, saves
them with a unique id (UUID) and sends them back by their id.

User defined port number may be set from the first command line
argument, otherwise the default value PORT is used.
"""

import cgi
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from os import path, makedirs
from socketserver import ThreadingTCPServer
from threading import Thread
from typing import Union
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

ADDRESS, PORT = '0.0.0.0', 8000

DATABASE = 'db.sqlite'
BASE_DIR = path.dirname(path.abspath(__file__))
FILEDIR = path.join(BASE_DIR, 'Uploads')


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
                query = f'''SELECT filepath, filename, extension
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
        '''Send the requested file to user.'''
        try:
            with open(filepath, 'rb') as file:
                self.send_response(code=200)
                self.send_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}{extension}"'
                )
                self.end_headers()
                downloading_content = file.read()
                print(f'Sending {filename}{extension}...')
                self.wfile.write(downloading_content)
                print('Done')

        except FileNotFoundError:
            self.send_response(code=410,
                               message=f'File with id {file_id} was deleted')
            self.end_headers()

    def do_GET(self) -> None:  # pylint: disable=C0103
        '''
        Check if the record for the given id exists in the DATABASE and
        send the respective response to user; if 'download' parameter
        provided, download the existing file to user from FILEPATH.
        Usage is as follows:

        CHECK
        http://<ADDRESS>:<PORT>/?id=<file_id>

        DOWNLOAD
        http://<ADDRESS>:<PORT>/?id=<file_id>&download=1
        '''
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

        filepath, filename, extension = db_response

        if 'download' not in params:
            self.send_response(code=200)
            self.end_headers()
            self.wfile.write(
                bytes(f'{filename}{extension}', 'utf-8'))
        else:
            self.send_file(file_id, filepath, filename, extension)

    def do_POST(self) -> None:  # pylint: disable=C0103
        '''
        Upload a file to the FILEPATH and create the record for that
        in the DATABASE, then send it's id in the response body.
        Usage is as follows:

        UPLOAD
        POST request containing the file body to http://<ADDRESS>:<PORT>/

        Files are saved as <uuid>.<extension> to prevent name duplication.
        '''
        uuid = str(uuid4())
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type']}
        )
        try:
            filename, extension = path.splitext(form.list[0].filename)
        except TypeError:
            filename = extension = 'not_provided'
        filepath = path.join(FILEDIR, f'{uuid}{extension}')

        with open(filepath, 'wb') as file:
            try:
                uploading_content = form.list[0].file.read()
                file.write(uploading_content)
                print(f'{filename}{extension} uploaded as {uuid}{extension}')
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
                conn.execute(query, {
                    'uuid': uuid,
                    'filepath': filepath,
                    'filename': filename,
                    'extension': extension,
                    'upload_date': datetime.now(),
                })
            conn.close()

            self.send_response(code=201)
            self.end_headers()
            self.wfile.write(bytes(uuid, 'utf-8'))

        except sqlite3.DatabaseError as error:
            self.send_response(code=500, message='Database error')
            self.end_headers()
            print('Database error :', error)


if __name__ == '__main__':
    try:
        INPUT_PORT = int(sys.argv[1])
        if INPUT_PORT not in range(65536):
            print('Port number must be 0-65535. Using the default value.')
        else:
            PORT = INPUT_PORT
    except ValueError:
        print('Port number must be an integer. Using the default value.')
    except IndexError:
        pass

    with ThreadingTCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving on port', PORT)
        SERVER_THREAD = Thread(httpd.serve_forever(), daemon=True)
        SERVER_THREAD.start()
