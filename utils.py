from songmash import app, db
from models import Artist
from bs4 import BeautifulSoup


def get_artist(artistid):

    if Artist.query.filter_by(artistid=artistid).first():
        return Artist.query.filter_by(artistid=artistid).first()
    else:
        artist = Artist(artistid)
        db.session.add(artist)
        db.session.commit()
        return artist
