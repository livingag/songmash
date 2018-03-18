from songmash import app, db
from models import Artist
from bs4 import BeautifulSoup
import requests
import wikipedia

def get_artist(name):

    if Artist.query.filter(Artist.name.ilike(name)).first():
        return Artist.query.filter(Artist.name.ilike(name)).first()
    else:
        artist = Artist(name)
        db.session.add(artist)
        db.session.commit()
        return artist
