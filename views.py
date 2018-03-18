from flask import render_template, request, url_for,jsonify, redirect
from songmash import app, db
from utils import get_artist
from models import *
import random


@app.route('/', methods=['GET', 'POST'])
def home():

    return render_template('home.html')


@app.route('/about')
def about():

    return render_template('about.html')


@app.route('/search', methods=['POST'])
def search():
    if request.method == 'POST':
        return redirect(url_for('voting',artist=request.form['artist']))


@app.route('/voting/<string:artist>')
def voting(artist):

    artist = get_artist(artist)

    tracks = []
    for album in artist.albums:
        for track in album.tracks:
            tracks.append(track)
    
    vs = random.sample(tracks,2)

    return render_template('voting.html',artist=artist.name,track1=vs[0],track2=vs[1])

@app.route('/ranking/<string:artist>')
def ranking(artist):

    artist = get_artist(artist)

    tracks = []
    for album in artist.albums:
        for track in album.tracks:
            tracks.append(track)

    tracks.sort(key=lambda x: x.elo, reverse=True)

    if [track.elo for track in tracks].count(1000) > (len(tracks)/2):
        return render_template('keepvoting.html',artist=artist.name)
    else:
        return render_template('ranking.html',artist=artist.name,tracks=tracks)

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