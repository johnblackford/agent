"""
Copyright (c) 2016 John Blackford

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# File Name: camera_ui.py
#
# Description: Camera User Interface (Bottle).
#
# Web Functionality:
#  - /static/<filename>
#    - serve_static(filename)
#  - /camera/<image_file_name>
#    - index(image_file_name)
#
# Class Functionality:
#  - CameraWebUI(host, port)
#    - set_db_conn(db_conn)
#    - serve_static_files(filename)
#    - show_picture(image_file_name)
#  - ThreadedCameraWebUI(db_file_name, host, port)
#    - run()
#  - Class Methods
#    - CameraWebUI.init_routes(web_app)
#    - CameraWebUI.start(web_app)
#
"""

import threading

import bottle



class CameraWebUI:
    """The Web UI for the USP Camera"""
    def __init__(self, host="localhost", port="8080", directory="pictures"):
        """Initialize the CameraWebUI"""
        self._host = host
        self._port = port
        self._directory = directory


    @classmethod
    def init_routes(cls, web_app):
        """Initialize the Bottle Routes as needed"""
        picture_route = "/" + web_app.get_directory() + "/<filename>"
        bottle.route("/camera/<image_file_name>")(web_app.show_picture)
        bottle.route(picture_route)(web_app.serve_static_images)
        bottle.route("/static/<filename>")(web_app.serve_static_files)

    @classmethod
    def start(cls, web_app):
        """Start the Bottle Web Server"""
        bottle.run(host=web_app.get_host(), port=web_app.get_port(), debug=True)

    def get_host(self):
        """Retrieve the Host Name"""
        return self._host

    def get_port(self):
        """Retrieve the Port Name"""
        return self._port

    def get_directory(self):
        """Retrieve the Directory"""
        return self._directory


    def serve_static_files(self, filename):
        """Web UI Page to show all static files"""
        return bottle.static_file(filename, root="./static")

    def serve_static_images(self, filename):
        """Web UI Page to show all static JPG files"""
        root_dir = "./" + self._directory
        return bottle.static_file(filename, root=root_dir)

    def show_picture(self, image_file_name):
        """Web UI Page to show all pictures"""
        timestamp = image_file_name.split("_")[1]
        filename = "/" + self._directory + "/" + image_file_name
        return bottle.template("camera_image", timestamp=timestamp, filename=filename)



class ThreadedCameraWebUI(threading.Thread):
    """Threaded Wrapper for the CameraWebUI Class"""
    def __init__(self, host="localhost", port="8080", directory="pictures"):
        """Initialize the ThreadedCameraWebUI and Create a CameraWebUI"""
        threading.Thread.__init__(self)
        self._web_app = CameraWebUI(host, port, directory)
        CameraWebUI.init_routes(self._web_app)


    def run(self):
        """Thread execution code - start the CameraWebUI"""
        CameraWebUI.start(self._web_app)



def main():
    """Main program for the testing the Camera Web UI"""
    # Threaded Version
#    web_app = ThreadedCameraWebUI("0.0.0.0", "8080", "pictures")
#    web_app.start()

    # Non-Threaded Version
    web_app = CameraWebUI("0.0.0.0", "8080", "pictures")
    CameraWebUI.init_routes(web_app)
    CameraWebUI.start(web_app)



if __name__ == "__main__":
    main()
