from socketserver import ThreadingTCPServer
from threading import Thread
import sqlite3
import re
from datetime import datetime
from os import getcwd, path, makedirs, mkdir
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

        file_id = params['id']

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

        if not db_response:
            self.send_response(code=204,
                               message=f'No files found with id {file_id}')
            self.end_headers()
            return

        filepath, filename, extension, upload_date = db_response

        if not 'download' in params:
            self.send_response(
                code=200,
                message=f'{filename}.{extension} was uploaded at {upload_date}'
            )
            self.end_headers()
            return
            
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
                code=410,
                message=f'File with id {file_id} was deleted.'
            )
            self.end_headers()
    
    def do_POST(self):
        '''
        Upload a file to FILEPATH and create the record for that
        in the DATABASE, then send it's id in the response message.
        '''
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length == 0:
            self.send_response(code=411, message='Length required')
            self.end_headers()
            return

        content_disposition = self.headers.get('Content-Disposition',
                                               'name="filename.not_provided"')
        filename, extension = re.findall(r'name="(.+)\.(\S+)"', 
                                         content_disposition)[0]
        
        file_content = self.rfile.read(content_length)
        uuid = uuid4()
        filepath = path.join(getcwd(), FILEDIR, f'{uuid}.{extension}')

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
                conn.execute(query, {'uuid': str(uuid), 
                                     'filepath': filepath,
                                     'filename': filename,
                                     'extension': extension,
                                     'upload_date': datetime.now()})
            conn.close()

            self.send_response(code=201, message=uuid)
            self.end_headers()

        except sqlite3.DatabaseError as e:
            self.send_response(code=500, message='Database error')
            self.end_headers()
            print('Database error :', e)


if __name__ == "__main__":
    with ThreadingTCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving on port', PORT)
        server_thread = Thread(httpd.serve_forever(), daemon=True)
        server_thread.start()
