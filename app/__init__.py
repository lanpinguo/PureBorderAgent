from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_pagedown import PageDown
from config import config

import socket
import sys
import os
import time

class BridgeREST():

    def __init__(self):
        # Create a UDS socket
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        
        # Connect the socket to the port where the server is listening
        self.server_address = '/tmp/borderAgent'
        self.client_address = '/tmp/borderTest'

        # Make sure the socket does not already exist
        try:
            os.unlink(self.client_address)
        except OSError:
            if os.path.exists(self.client_address):
                raise

        print( 'connecting to %s' % self.server_address)
        try:
            self.sock.bind(self.client_address)
        except (socket.error) as msg:
            print(msg)
    
    def post(self,ip,res,payload):
        result = b''
        try:
            # Send data
            message = b'post' + b'://[%d]' % len(res) + b'/' \
                + b'[' + ip + b']'+ b'/' +  res + payload
            print(message)
            self.sock.sendto(message,self.server_address)

            wait_cnt = 10
            while  wait_cnt > 0 :
                try:
                    result = self.sock.recv(4096, 0x40)
                    break
                except BlockingIOError as e:
                    time.sleep(0.1)
                    wait_cnt -= 1
                    
            print( 'received "%s"' % result)
        finally:
            return result

    def get(self,ip,res):
        result = b''
        try:
            # Send data
            print(ip)
            message = b'get' + b'://[%d]' % len(res) + b'/' \
                + b'[' + ip + b']'+ b'/' +  res
            print(  message)
            self.sock.sendto(message,self.server_address)
        
            wait_cnt = 10
            while  wait_cnt > 0 :
                try:
                    result = self.sock.recv(4096, 0x40)
                    break
                except BlockingIOError as e:
                    time.sleep(0.1)
                    wait_cnt -= 1

            print( 'received "%s"' % result)
        finally:
            return result

    def close(self):
        print( 'closing socket')
        self.sock.close()




bg = BridgeREST()
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    return app
