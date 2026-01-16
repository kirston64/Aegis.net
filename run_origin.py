import http.server
import socketserver
import os

PORT = 9000
DIRECTORY = "website"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def start_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Allow address reuse to avoid "Address already in use" errors during restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"==================================================")
        print(f"🏠 ORIGIN SERVER (The 'Real' Site) running on port {PORT}")
        print(f"👉 http://localhost:{PORT}")
        print(f"==================================================")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping origin server...")
            httpd.server_close()

if __name__ == "__main__":
    start_server()
