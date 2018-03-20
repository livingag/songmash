from flask import render_template, request, url_for,jsonify, redirect
from songmash import app, db
from utils import get_artist
from models import *
import random
from profanity import profanity


@app.route('/', methods=['GET', 'POST'])
def home():
    if len(Artist.query.all()) > 2:
        artlist = random.sample(Artist.query.all(),3)
    else:
        artlist = None
    return render_template('home.html',artlist=artlist)


@app.route('/about')
def about():

    return render_template('about.html')


@app.route('/search', methods=['POST'])
def search():
    if request.method == 'POST':
        name = request.form['artist']
        if Artist.query.filter(Artist.name.ilike(name)).first():
            artist = Artist.query.filter(Artist.name.ilike(name)).first()
            return redirect(url_for('voting',artistid=artist.artistid))
        else:
            return redirect(url_for('new_artist',artist=request.form['artist']))


@app.route('/newartist/<string:artist>')
def new_artist(artist):
    out = []
    for artist in musicbrainzngs.search_artists(artist)['artist-list']:
        if not profanity.contains_profanity(artist['name']):
            if 'disambiguation' in artist.keys():
                out.append([artist['name']+' ('+artist['disambiguation']+')',artist['id']])
            else:
                out.append([artist['name'],artist['id']])

    return render_template('newartist.html', list=out[:10])


@app.route('/voting/<string:artistid>')
def voting(artistid):

    artist = get_artist(artistid)

    tracks = []
    for album in artist.albums:
        for track in album.tracks:
            tracks.append(track)

    vs = random.sample(tracks,2)

    return render_template('voting.html',artist=artist,track1=vs[0],track2=vs[1])

@app.route('/ranking/<string:artistid>')
def ranking(artistid):

    artist = get_artist(artistid)

    tracks = []
    albums = []

    for album in artist.albums:
        album.calculate_mean_elo()
        albums.append(album)
        for track in album.tracks:
            tracks.append(track)

    tracks.sort(key=lambda x: x.elo, reverse=True)
    albums.sort(key=lambda x: x.mean_elo, reverse=True)

    if [track.elo for track in tracks].count(1000) > (len(tracks)/2):
        return render_template('keepvoting.html',artist=artist.name)
    else:
        return render_template('ranking.html',artist=artist,tracks=tracks,albums=albums)

@app.route('/_adjust_elo')
def adjust_elo():
    winner = request.args.get('winner', 0, type=int)
    loser = request.args.get('loser', 0, type=int)

    winner = Track.query.filter_by(id=winner).first()
    loser = Track.query.filter_by(id=loser).first()

    winner.adjust_elo_win(loser)

    db.session.add(winner)
    db.session.add(loser)
    db.session.commit()

    end = 1

    return jsonify(end=end)


@app.route('/_get_plot_data')
def get_plot_data():
    artist = request.args.get('artist',0)

    artist = get_artist(artist)

    data = []
    no = 1
    tracknames = []
    for album in artist.albums:
        trackdata = []
        for track in album.tracks:
            trackdata.append([no,track.elo])
            tracknames.append(track.name)
            no+=1
        data.append({
            'label': album.name,
            'data': trackdata
        })
    data = [data,tracknames]
    return jsonify(data)