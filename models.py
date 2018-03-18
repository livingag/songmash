from songmash import app, db
from bs4 import BeautifulSoup
import requests
import wikipedia


class Artist(db.Model):
    __tablename__ = 'artists'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(40))
    albums = db.relationship('Album')

    def __init__(self,name):
        name = wikipedia.search(name+' singer band')[0]

        wiki = wikipedia.page(name)
        soup = BeautifulSoup(wiki.html(),"lxml")
        
        discog = soup.find('span', {'id': 'Discography'}).findNext('ul')
        
        self.albums = [Album(self.name,al.contents[0],al['title']) for al in discog.find_all('a')]
        
        for title in ['band','singer','musician']:
            name = name.replace(' ({})'.format(title),'')
        
        self.name = name


class Album(db.Model):
    __tablename__ = 'albums'
    id = db.Column(db.Integer(), primary_key=True)
    artistid = db.Column(db.Integer(), db.ForeignKey('artists.id'))
    name = db.Column(db.String(40))
    title = db.Column(db.String(40))
    art = db.Column(db.String(200))
    tracks = db.relationship('Track')

    def __init__(self,artist,name,title):
        self.artist = artist
        self.name = name
        self.title = title

        wiki = wikipedia.page(self.title)
        soup = BeautifulSoup(wiki.html(), "lxml")
        
        self.art = soup.find('table',{'class':'infobox'}).findNext('img')['src']
        
        table = soup.find('span', {'id': 'Track_listing'}).findNext('table')
        rows = table.find_all('tr')
        data = []
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele])
                
        self.tracks = []
        for song in data[1:]:
            if len(song) > 2:
                self.tracks.append(Track(song[1].split(song[1][0])[1],self.artist,self.name,self.art))

    def __repr__(self):
        return self.name


class Track(db.Model):
    __tablename__ = 'tracks'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(40))
    albumid = db.Column(db.Integer(), db.ForeignKey('albums.id'))
    album = db.Column(db.String(40))
    art = db.Column(db.String(200))
    elo = db.Column(db.Integer())

    def __init__(self,name,artist,album,art):
        self.name = name
        self.artist = artist
        self.album = album
        self.art = art
        self.elo = 1000
    def __repr__(self):
        return self.name
    def adjust_elo_win(self,opponent):
        R1 = 10**(self.elo/400)
        R2 = 10**(opponent.elo/400)
        E1 = R1 / (R1 + R2)
        E2 = R2 / (R1 + R2)
        self.elo += int(32 * (1 - E1))
        opponent.elo += int(32 * (0 - E2))
