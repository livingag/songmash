from songmash import app, db
from bs4 import BeautifulSoup
import requests
import musicbrainzngs
from bs4 import BeautifulSoup


class Artist(db.Model):
    __tablename__ = 'artists'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(40))
    artistid = db.Column(db.String(40))
    albums = db.relationship('Album')

    def __init__(self,artistid):
        artist = musicbrainzngs.get_artist_by_id(
            artistid,
            includes=["release-groups"],
            release_type=["album"]
        )['artist']

        self.name = artist['name']
        self.artistid = artistid

        releasegroups = artist['release-group-list']

        albums = []
        releases = []
        for release in releasegroups:
            if release['type'] == 'Album' and \
               all(k not in release.keys() for k in ['disambiguation','secondary-type-list']):
                releases.append(release)
        releases.sort(key=lambda x: x['first-release-date'])
        albumids = [release['id'] for release in releases]

        if len(albumids) <= 1:
            raise ValueError()

        for albumid in albumids:

            releases = musicbrainzngs.get_release_group_by_id(albumid,includes=["releases"])['release-group']['release-list']

            us = []
            for rel in releases:
                if 'disambiguation' not in rel.keys() and \
                   all(k in rel.keys() for k in ['country','date','status']) and \
                   rel['status'] == 'Official':
                    if rel['country'] in ['US','GB','XE']:
                        us.append(rel)

            us.sort(key=lambda x: x['date'])

            nalbums = len(albums)
            for rel in us:
                album = musicbrainzngs.get_release_by_id(rel['id'],includes=['recordings','artists'])['release']
                if len(album['artist-credit']) == 1:
                    if 'format' in album['medium-list'][0].keys() and \
                    album['cover-art-archive']['artwork'] == 'true':
                        if album['medium-list'][0]['format'] == 'Digital Media':
                            albums.append(album)
                            break
                        elif album['medium-list'][0]['format'] == 'CD':
                            albums.append(album)
                            break
            
            if len(albums) == nalbums:
                for rel in us:
                    album = musicbrainzngs.get_release_by_id(rel['id'],includes=['recordings','artists'])['release']
                    if len(album['artist-credit']) == 1:
                        if 'format' in album['medium-list'][0].keys():
                            if album['medium-list'][0]['format'] == 'Digital Media':
                                albums.append(album)
                                break
                            elif album['medium-list'][0]['format'] == 'CD':
                                albums.append(album)
                                break

        self.albums = [Album(album,self.name) for album in albums]


class Album(db.Model):
    __tablename__ = 'albums'
    id = db.Column(db.Integer(), primary_key=True)
    artistid = db.Column(db.Integer(), db.ForeignKey('artists.id'))
    name = db.Column(db.String(40))
    title = db.Column(db.String(40))
    art = db.Column(db.String(200))
    tracks = db.relationship('Track', backref='album', lazy=True)

    def __init__(self,album,artist):
        self.artist = artist
        self.name = album['title']
        self.get_album_art(album)
        self.tracks = []
        for disc in album['medium-list']:
            for track in disc['track-list']:
                self.tracks.append(Track(track['recording']['title'],
                                     self.artist))

    def __repr__(self):
        return self.name

    def get_album_art(self,album):
        art = requests.get('http://coverartarchive.org/release/{}'.format(album['id']))
        if art.status_code == 404:
            try:
                asin = album['asin']
                r = requests.get('http://www.amazon.com/gp/product/{}'.format(asin))
                soup = BeautifulSoup(r.text,"lxml")
                self.art = soup.find('img', {'alt': album['title']})['src']
            except:
                self.art = "{{ url_for('static', filename='img/noart.png') }}"
        elif art.status_code == 502:
            time.sleep(0.5)
            art = requests.get('http://coverartarchive.org/release/{}'.format(album['id']))
        else:
            self.art = art.json()['images'][0]['thumbnails']['small']

    def calculate_mean_elo(self):
        if len(self.tracks) > 0:
            tracks = [track.elo for track in self.tracks]
            self.mean_elo = sum(tracks)/len(tracks)
        else:
            self.mean_elo = 0


class Track(db.Model):
    __tablename__ = 'tracks'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(40))
    albumid = db.Column(db.Integer(), db.ForeignKey('albums.id'))
    elo = db.Column(db.Integer())

    def __init__(self,name,artist):
        self.name = name
        self.artist = artist
        self.elo = 1000
    def __repr__(self):
        return self.name
    def adjust_elo_win(self,opponent):
        R1 = 10**(self.elo/400)
        R2 = 10**(opponent.elo/400)
        E1 = R1 / (R1 + R2)
        E2 = R2 / (R1 + R2)
        self.elo += 32 * (1 - E1)
        opponent.elo += 32 * (0 - E2)
