import socketserver
import sqlite3
import re
from datetime import datetime
from os import path, getcwd, listdir, mkdir
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qsl
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
        Check if a file with the given id exists in the FILEPATH folder
        and send the respective response to user; if 'download' 
        parameter provided, download the existing file to user.
        '''
        get_query = urlsplit(self.path).query
        params = dict(parse_qsl(get_query))

        if 'id' in params:
            file_id = params['id']

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            query = f'''SELECT filename, extension, upload_date
                        FROM filepaths 
                        WHERE uuid=:id;
                    '''
            cursor.execute(query, {'id': file_id})
            db_response = cursor.fetchone()
            conn.close()

            if db_response:
                filename, extension, upload_date = db_response
            
                if 'download' in params:
                    self.send_response(code=200)
                    self.end_headers()

                    with open(path.join(FILEPATH, f'{file_id}.{extension}'), 'rb') as file:
                        data = file.read()
                        self.wfile.write(data)
                else:
                    self.send_response(
                        code=200,
                        message=f'File {filename}.{extension} uploaded at {upload_date}'
                    )
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
        Upload a file to the server file system and 
        get back it's new id as a response message.
        '''
        content_length = int(self.headers['Content-Length'])

        file_content = self.rfile.read(content_length)
        file_name = re.findall(r'name="([^/\\:*?"<>|]+)\.\w+"$',
                               self.headers['Content-Disposition'])[0]
        file_extension = re.findall(r'\.(\w+)"$', 
                                    self.headers['Content-Disposition'])[0]
        
        uuid = uuid4()

        with open(path.join(FILEPATH, f"{uuid}.{file_extension}"), 'wb') as file:
            file.write(file_content)
        
        conn = sqlite3.connect(DATABASE)
        with conn:
            query = f'''INSERT INTO filepaths VALUES (
                            :uuid,
                            :filename,
                            :extension,
                            :upload_date
                        );'''
            conn.execute(query, {'uuid': str(uuid), 
                                 'filename': file_name,
                                 'extension': file_extension,
                                 'upload_date': datetime.now()})
        conn.close()

        self.send_response(code=201, message=f'File saved with id {uuid}')
        self.end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving at port', PORT)
        httpd.serve_forever()
