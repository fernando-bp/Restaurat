from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import sys
import os

class TokenHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/token'):
            try:
                # Run the test_factus_token.py script using the same Python executable
                proc = subprocess.run([sys.executable, 'test_factus_token.py'], capture_output=True, text=True, cwd=os.getcwd())
                if proc.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(proc.stdout.encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(proc.stderr.encode('utf-8'))
            except Exception as exc:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(str(exc).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=TokenHandler, port=8000):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print(f'Serving on http://0.0.0.0:{port} (GET /token)')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down')
        httpd.server_close()

if __name__ == '__main__':
    run()
