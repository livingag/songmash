from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import musicbrainzngs

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

app.config.update(
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db'),
    SQLALCHEMY_ECHO = False,
)

db = SQLAlchemy(app)

musicbrainzngs.set_useragent("songmash","0.1","http://songmash.me")

import views, models, utils

if not os.path.exists(os.path.join(basedir, 'app.db')):
    db.create_all()
