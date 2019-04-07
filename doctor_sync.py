import socketserver
import sqlite3
import re
from datetime import datetime
from os import path, getcwd, mkdir
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qsl
from contextlib import closing
from uuid import uuid4


ADDRESS, PORT = '127.0.0.1', 5050

DATABASE = 'db.sqlite'
FILEPATH = path.join(getcwd(), 'Uploads')

if not path.isdir(FILEPATH):
    mkdir(FILEPATH)

if not path.isfile(DATABASE):
    conn = sqlite3.connect(DATABASE)
    with conn:
        conn.execute('''CREATE TABLE filepaths (
                            uuid CHARACTER(36) PRIMARY KEY,
                            filename TEXT NOT NULL,
                            extension TEXT,
                            upload_date TEXT
                        );''')
    conn.close()
    

class HttpHandler(BaseHTTPRequestHandler):
    "A tiny request handler for uploading and downloading files."

    def do_GET(self):
        '''
        Check if a record for the given id exists in the DATABASE and
        send the respective response to user; if 'download' parameter 
        provided, download the existing file to user from FILEPATH.
        '''
        get_query = urlsplit(self.path).query
        params = dict(parse_qsl(get_query))

        if 'id' in params:
            file_id = params['id']

            try:
                with closing(sqlite3.connect(DATABASE)) as conn:
                    cursor = conn.cursor()
                    query = f'''SELECT filename, extension, upload_date
                                FROM filepaths 
                                WHERE uuid=:id;
                            '''
                    cursor.execute(query, {'id': file_id})
                    db_response = cursor.fetchone()

            except sqlite3.DatabaseError as e:
                self.send_response(code=500, message='Database error')
                self.end_headers()
                print('Database error :', e)

            if db_response:
                filename, extension, upload_date = db_response
            
                if 'download' in params:
                    self.send_response(code=200)
                    self.end_headers()

                    try:
                        filepath = path.join(FILEPATH, f'{file_id}.{extension}')
                        with open(filepath, 'rb') as file:
                            data = file.read()
                            self.wfile.write(data)

                    except FileNotFoundError:
                        self.send_response(
                            code=404, 
                            message=f'File with id {file_id} was deleted.')
                        self.end_headers()
                else:
                    self.send_response(
                        code=200,
                        message=f'File {filename}.{extension} uploaded at {upload_date}')
                    self.end_headers()
            else:
                self.send_response(code=404, 
                                   message=f'No files found with id {file_id}')
                self.end_headers()
        else:
            self.send_response_only(code=200)
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

        file_content = self.rfile.read(content_length)
        header = re.findall(r'name="(.+)"', self.headers['Content-Disposition'])
        filename, extension = header[0].split('.')
        
        uuid = uuid4()

        with open(path.join(FILEPATH, f'{uuid}.{extension}'), 'wb') as file:
            file.write(file_content)
        
        try:
            with sqlite3.connect(DATABASE) as conn:
                query = '''INSERT INTO filepaths VALUES (
                               :uuid,
                               :filename,
                               :extension,
                               :upload_date
                           );'''
                conn.execute(query, {'uuid': str(uuid), 
                                     'filename': filename,
                                     'extension': extension,
                                     'upload_date': datetime.now()})
            conn.close()

            self.send_response(code=201, message=f'File saved with id {uuid}')
            self.end_headers()

        except sqlite3.DatabaseError as e:
            self.send_response(code=500, message='Database error')
            self.end_headers()
            print('Database error :', e)


if __name__ == "__main__":
    with socketserver.TCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving at port', PORT)
        httpd.serve_forever()
