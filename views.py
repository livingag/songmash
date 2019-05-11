from flask import render_template, request, url_for, jsonify, redirect, flash, session
from songmash import app, db
from utils import get_artist
from models import *
import random
from profanity import profanity
import urllib
import spotipy
from spotipy import oauth2
import base64
import json
import six


@app.route("/", methods=["GET", "POST"])
def home():
    if "spotify-token" in session:
        try:
            token = session["spotify-token"]
            sp = spotipy.Spotify(auth=token)
            topartists = sp.current_user_top_artists(time_range="long_term", limit=10)
        except:
            return redirect(url_for("logout_spotify"))

        return render_template("home.html", artlist=topartists["items"])
    else:
        return render_template("home.html")


@app.route("/about")
def about():

    return render_template("about.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        name = request.form["artist"]
    else:
        name = request.args.get("artist")

    if Artist.query.filter(Artist.name.ilike(name)).first():
        artist = Artist.query.filter(Artist.name.ilike(name)).first()
        return redirect(url_for("voting", artistid=artist.artistid))
    else:
        return redirect(url_for("new_artist", artist=name))


@app.route("/newartist/<string:artist>")
def new_artist(artist):
    out = []
    for artist in musicbrainzngs.search_artists(artist)["artist-list"]:
        if not profanity.contains_profanity(artist["name"]):
            if "disambiguation" in artist.keys():
                out.append(
                    [
                        artist["name"] + " (" + artist["disambiguation"] + ")",
                        artist["id"],
                    ]
                )
            else:
                out.append([artist["name"], artist["id"]])

    return render_template("newartist.html", list=out[:10])


@app.route("/voting/<string:artistid>")
def voting(artistid):

    artist = get_artist(artistid)

    tracks = []
    for album in artist.albums:
        for track in album.tracks:
            tracks.append(track)

    vs = random.sample(tracks, 2)

    if "spotify-token" in session:
        token = session["spotify-token"]
        sp = spotipy.Spotify(auth=token)
        for v in vs:
            track = " ".join(v.name.lower().split()[::3])
            album = v.album.name.lower()
            result = sp.search(q="{} {} {}".format(artist.name, track, album))
            if len(result["tracks"]["items"]) > 0:
                v.spid = result["tracks"]["items"][0]["id"]

    return render_template("voting.html", artist=artist, track1=vs[0], track2=vs[1])


@app.route("/ranking/<string:artistid>")
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

    if [track.elo for track in tracks].count(1000) > (len(tracks) / 2):
        return render_template("keepvoting.html", artist=artist)
    else:
        return render_template(
            "ranking.html", artist=artist, tracks=tracks, albums=albums
        )


@app.route("/update/<string:artistid>")
def update_artist(artistid):

    newartist = Artist(artistid)
    oldartist = Artist.query.filter_by(artistid=artistid).first()

    updated = False

    for album in oldartist.albums:
        if album.name not in [a.name for a in newartist.albums]:
            for track in album.tracks:
                db.session.delete(track)
            db.session.delete(album)
            updated = True
        else:
            ind = [a.name for a in newartist.albums].index(album.name)
            newalbum = newartist.albums[ind]
            for track in album.tracks:
                if track.name not in [t.name for t in newalbum.tracks]:
                    db.session.delete(track)
                    updated = True

    for album in newartist.albums:
        if album.name not in [a.name for a in oldartist.albums]:
            oldartist.albums.insert(newartist.albums.index(album), album)
            updated = True
        else:
            ind = [a.name for a in oldartist.albums].index(album.name)
            oldalbum = oldartist.albums[ind]
            for track in album.tracks:
                if track.name not in [t.name for t in oldalbum.tracks]:
                    newtrack = Track(track.name, track.artist)
                    oldalbum.tracks.insert(album.tracks.index(track), newtrack)
                    updated = True

    db.session.commit()

    if updated == True:
        flash("Artist successfully updated!", "success")
    else:
        flash("Artist already up to date!", "info")

    return redirect(url_for("voting", artistid=oldartist.artistid))


@app.route("/login-spotify")
def login_spotify():

    auth_query_parameters = {
        "response_type": "code",
        "redirect_uri": app.config["REDIRECT_URI"] + url_for("auth"),
        "scope": "user-top-read",
        "client_id": app.config["CLIENT_ID"],
    }

    url_args = "&".join(
        [
            "{}={}".format(key, urllib.parse.quote(val))
            for key, val in auth_query_parameters.items()
        ]
    )
    auth_url = "{}/?{}".format("https://accounts.spotify.com/authorize", url_args)
    return redirect(auth_url)


@app.route("/logout-spotify")
def logout_spotify():

    session.pop("spotify-token", None)
    return redirect(url_for("home"))


@app.route("/auth")
def auth():

    auth_token = request.args["code"]
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": app.config["REDIRECT_URI"] + url_for("auth"),
    }
    bstring = six.text_type(
        "{}:{}".format(app.config["CLIENT_ID"], app.config["CLIENT_SECRET"])
    )
    base64encoded = base64.b64encode(bstring.encode("ascii"))
    headers = {"Authorization": "Basic {}".format(base64encoded.decode("ascii"))}
    post_request = requests.post(
        "https://accounts.spotify.com/api/token", data=code_payload, headers=headers
    )

    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    session["spotify-token"] = access_token

    return redirect(url_for("home"))


@app.route("/_adjust_elo", methods=["GET", "POST"])
def adjust_elo():
    if request.method == "POST":
        data = request.get_json()
        winner = data["winner"]
        loser = data["loser"]

        winner = Track.query.filter_by(id=winner).first()
        loser = Track.query.filter_by(id=loser).first()

        winner.adjust_elo_win(loser)

        db.session.add(winner)
        db.session.add(loser)
        db.session.commit()

        end = 1

        return jsonify(end=end)
    else:
        return redirect(url_for("home"))


@app.route("/_get_plot_data")
def get_plot_data():
    artist = request.args.get("artist", 0)

    artist = get_artist(artist)

    data = []
    no = 1
    tracknames = []
    for album in artist.albums:
        trackdata = []
        for track in album.tracks:
            trackdata.append([no, track.elo])
            tracknames.append(track.name)
            no += 1
        data.append({"label": album.name, "data": trackdata})
    data = [data, tracknames]
    return jsonify(data)

