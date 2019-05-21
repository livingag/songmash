from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import os
import musicbrainzngs

csrf = CSRFProtect()

app = Flask(__name__)
csrf.init_app(app)

basedir = os.path.abspath(os.path.dirname(__file__))

app.config.update(
    SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(basedir, "app.db"),
    SQLALCHEMY_ECHO=False,
    SECRET_KEY="40c2dc59fc221f675231bcd9e2374e29bcbf0edc1704c2f0",
)

app.config.from_pyfile("spotify.cfg")

db = SQLAlchemy(app)

musicbrainzngs.set_useragent("songmash", "0.1", "http://songmash.me")

import views, models, utils

if app.debug == True:
    admin = Admin(app)
    admin.add_view(ModelView(models.Artist, db.session))
    admin.add_view(ModelView(models.Album, db.session))
    admin.add_view(ModelView(models.Track, db.session))

    if not os.path.exists(os.path.join(basedir, "app.db")):
        db.create_all()
