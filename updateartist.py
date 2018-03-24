from songmash import app, db
from models import *

artistid = '437a0e49-c6ae-42f6-a6c1-84f25ed366bc'

newartist = Artist(artistid)
oldartist = Artist.query.filter_by(artistid=artistid).first()

for album in oldartist.albums:
    if album.name not in [a.name for a in newartist.albums]:
        for track in album.tracks:
            db.session.delete(track)
        db.session.delete(album)
    else:
        ind = [a.name for a in newartist.albums].index(album.name)
        newalbum = newartist.albums[ind]
        for track in album.tracks:
            if track.name not in [t.name for t in newalbum.tracks]:
                db.session.delete(track)

for album in newartist.albums:
    if album.name not in [a.name for a in oldartist.albums]:
        oldartist.albums.insert(newartist.albums.index(album),album)
    else:
        ind = [a.name for a in oldartist.albums].index(album.name)
        oldalbum = oldartist.albums[ind]
        for track in album.tracks:
            if track.name not in [t.name for t in oldalbum.tracks]:
                newtrack = Track(track.name,track.artist)
                oldalbum.tracks.insert(album.tracks.index(track),newtrack) 

db.session.commit()