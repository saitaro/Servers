import socketserver
import re
from os import path, getcwd, listdir
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qsl
from uuid import uuid4


ADDRESS, PORT = '127.0.0.1', 5050

FILEPATH = getcwd()


class HttpHandler(BaseHTTPRequestHandler):
    "A tiny request handler for uploading and downloading files."

    def do_GET(self):
        """
        Check if a file with the given id exists in the FILEPATH folder
        and send the respective response to user; if 'download' 
        parameter provided, download the existing file to user.
        """
        get_query = urlsplit(self.path).query
        params = dict(parse_qsl(get_query))

        if 'id' in params:
            file_id = params['id']

            for filename in listdir(FILEPATH):
                if re.match(file_id, filename):
                    if 'download' in params:
                        self.send_response(code=200)
                        self.end_headers()
                        with open(filename, 'rb') as file:
                            self.wfile.write(file.read())
                    else:
                        self.send_response(code=200,
                                           message=f'File exists as {filename}')
                        self.end_headers()
                    break
            else:
                self.send_response(code=404, 
                                   message=f'No files found with id {file_id}')
                self.end_headers()
        else:
            self.send_response_only(code=200)
            self.end_headers()

    def do_POST(self):
        """
        Upload a file to the server file system and 
        get back it's new id as a response message.
        """
        content_length = int(self.headers['Content-Length'])
        file_content = self.rfile.read(content_length)
        file_extension = re.findall(r'\.(\w+)"$', 
                                    self.headers['Content-Disposition'])[0]
        uuid = uuid4()

        with open(f"{uuid}.{file_extension}", 'wb') as file:
            file.write(file_content)

        self.send_response(code=201, message=f'File saved with id {uuid}')
        self.end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer((ADDRESS, PORT), HttpHandler) as httpd:
        print('Serving at port', PORT)
        httpd.serve_forever()
