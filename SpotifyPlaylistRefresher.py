#!/usr/bin/python3

# Author: Gokul Pillai
# Spotify Playlist Refresher
# This is an application that allows users to delete un-used songs from their playlists. The algorithm to determine
# songs to delete is that it checks if the song is either in the users top songs or is a song of one of the user's top 
# artists, and if not, it is added to the delete list. The user is given the option of selecting any songs to keep
# before the app deletes them.

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_wtf import FlaskForm
from wtforms import SelectField, widgets, SelectMultipleField
import os
import shutil
import spotipy
import uuid
import signal
import threading
import logging
from spotipy.oauth2 import SpotifyOAuth

SERVER_IP = "0.0.0.0"
SERVER_PORT=443
REDIR_HOST = "www.playlistrefresher.com/refresher"
MY_REDIR_URL="https://" + REDIR_HOST

# g_DICT is a dictionary of each session. There seems
# to be some issue when flask session is assigned the
# sp object - gives an error about jsonifying.
# Hence this is used, we create a random number for
# each session in setup()
g_DICT = {}

# NOTE: Spotify credentials
# If not specified in the environment, do specify it here.
#os.environ["SPOTIPY_CLIENT_ID"]="XXXXXXXXXXXX"
#os.environ["SPOTIPY_CLIENT_SECRET"]="YYYYYYYYYY"

os.environ["SPOTIPY_REDIRECT_URI"]=MY_REDIR_URL

caches_folder = '/tmp/.spotify_caches/'
if not os.path.exists(caches_folder):
        os.makedirs(caches_folder)

app = Flask(__name__, static_url_path='/templates')
app.config['SECRET_KEY'] = str(uuid.uuid4())
logging.basicConfig(level=logging.INFO)

if not "SPOTIPY_CLIENT_ID" in os.environ:
        app.logger.error("SPOTIPY_CLIENT_ID environment variable must be set!")
        exit(255)
if not "SPOTIPY_CLIENT_SECRET" in os.environ:
        app.logger.error("SPOTIPY_CLIENT_SECRET environment variable must be set!")
        exit(255)

def sig_handler(signum, stack):
    try:
        shutil.rmtree(caches_folder)
    except:
        pass
    exit(255)

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGPIPE, sig_handler)


class Song():
    # Notify systemd that the service is ready, otherwise
    # service startup won't exit and will kill our process
    # after some time and will repeat that
    cmd = "systemd-notify --ready"
    os.system(cmd)

    song_uri = ''
    song_name = ''


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class Form(FlaskForm):
    global g_DICT

    playlist = SelectField('playlist', choices = [])

    Nil = Song()
    Nil.song_uri = 'Nil'
    Nil.song_name = 'None'

    song = MultiCheckboxField('Label', choices = [])


@app.route('/refresher', methods=['GET', 'POST'])
def setup():
    global g_DICT
    scope = 'user-top-read playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private'

    tid = str(uuid.uuid4())
    session['tid'] = tid

    if not tid in g_DICT:
        # Initialize dictionary of dictionaries
        # keyed with thread id
        g_DICT[tid] = {}

    if not 'mycache' in session:
        session['mycache'] = caches_folder + str(uuid.uuid4())

    auth_manager = spotipy.oauth2.SpotifyOAuth(scope=scope,
                                               cache_path=session['mycache'],
                                               show_dialog=True)

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/refresher')

    if not auth_manager.get_cached_token():
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return redirect(auth_url)

    # Step 4. Signed in, display data
    sp = spotipy.Spotify(auth_manager=auth_manager)
    username = sp.me()["display_name"]
    if not 'username' in session:
        session['username'] = username
        app.logger.info("New user login: %s", username)

    #accumulating all of the user's top tracks
    results = sp.current_user_top_tracks(50,0,"short_term")
    top_tracks = [item['name'] for item in results['items']]
    results = sp.current_user_top_tracks(50,49,"short_term")
    top_tracks.extend([item['name'] for item in results['items'][1:]])

    results = sp.current_user_top_tracks(50,0,"medium_term")
    top_tracks.extend([item['name'] for item in results['items']])
    results = sp.current_user_top_tracks(50,49,"medium_term")
    top_tracks.extend([item['name'] for item in results['items'][1:]])

    results = sp.current_user_top_tracks(50,0,"long_term")
    top_tracks.extend([item['name'] for item in results['items']])
    results = sp.current_user_top_tracks(50,49,"long_term")
    top_tracks.extend([item['name'] for item in results['items'][1:]])

    #accumulating all of the user's top artists
    results = sp.current_user_top_artists(50,0,"short_term")
    top_artists = [item['name'] for item in results['items']]
    results = sp.current_user_top_artists(50,49,"short_term")
    top_artists.extend([item['name'] for item in results['items'][1:]])

    results = sp.current_user_top_artists(50,0,"medium_term")
    top_artists.extend([item['name'] for item in results['items']])
    results = sp.current_user_top_artists(50,49,"medium_term")
    top_artists.extend([item['name'] for item in results['items'][1:]])

    results = sp.current_user_top_artists(50,0,"long_term")
    top_artists.extend([item['name'] for item in results['items']])
    results = sp.current_user_top_artists(50,49,"medium_term")
    top_artists.extend([item['name'] for item in results['items'][1:]])

    playlist_items = [('None','Choose a Playlist')]
    all_playlists = sp.current_user_playlists()
    #accumulating all of the user's playlists
    while all_playlists:
        for item in all_playlists['items']:
            if(item['owner']['display_name'] == username):
                playlist_items.append((item['uri'],item['name']))
            elif(item['collaborative']):
                playlist_items.append((item['uri'],item['name']))

        all_playlists = sp.next(all_playlists)

    g_DICT[tid]["sp"] = sp
    g_DICT[tid]["username"] = username
    g_DICT[tid]["top_tracks"] = top_tracks
    g_DICT[tid]["top_artists"] = top_artists
    g_DICT[tid]["playlist_items"] = playlist_items
    g_DICT[tid]["playlist_uri"] = ""
    g_DICT[tid]["del_tracks"] = []
    g_DICT[tid]["songChoices"] = []

    return redirect(url_for('main'))


@app.route('/main/', methods=['GET', 'POST'])
def main():
    global g_DICT

    tid = session['tid']

    form = Form()
    if tid in g_DICT:
        form.playlist.choices = [items[1] for items in g_DICT[tid]["playlist_items"]]
    else:
        form.playlist.choices = []

    #if one of the submit buttons were pressed 
    if request.method == "POST":
        #if the username submit button was pressed
        if "signOut" in request.form:
            try:
                # Remove the CACHE file (.cache-test) so that a new user can authorize.
                os.remove(session['mycache'])
            except OSError as e:
                print ("Error: %s - %s." % (e.filename, e.strerror))
            g_DICT.pop(tid)
            return redirect('/')

        checkboxList = request.form.getlist('mycheckbox')
        delete = []
        deleteOut = []
        for track in g_DICT[tid]["del_tracks"]:
            if(track[0] in checkboxList):
                delete.append(track[0])
                deleteOut.append(track[1])

        g_DICT[tid]["sp"].user_playlist_remove_all_occurrences_of_tracks(
                    g_DICT[tid]["username"],
                    g_DICT[tid]["playlist_uri"], delete)
       
        return redirect("/refresher")

    return render_template('refresher.html', form=form)

#displaying the songs to be deleted based on which playlist was chosen
@app.route('/song/<playlist>', methods=['GET', 'POST'])
def songFunc(playlist):
    global g_DICT

    del_tracks = []

    tid = session['tid']

    sp = g_DICT[tid]["sp"]
    username = g_DICT[tid]["username"]
    playlist_items = g_DICT[tid]["playlist_items"]
    playlist_uri = g_DICT[tid]["playlist_uri"]
    top_artists = g_DICT[tid]["top_artists"]
    top_tracks = g_DICT[tid]["top_tracks"]

    playlist_uri = list(filter(lambda x: x[1] == playlist, playlist_items))[0][0]
   
    #checks if the song is either in the users top songs or is a song of one of the user's top artists, and if not, it is added to the delete list
    playlist_info = sp.user_playlist_tracks(username, playlist_uri)
    while playlist_info:
        for item in playlist_info['items']:
            if(not item['track']['name']):
                continue
            delete = True
            temp_nameList = []
            for name in item['track']['artists']:
                temp_nameList.append(name['name'])
            for name in top_artists:
                if(name in temp_nameList):
                    delete = False
                    break
            if(delete):
                for track in top_tracks:
                    if(track == item['track']['name']):
                        delete = False
                        break
            if(delete):
                del_tracks.append((item['track']['uri'],item['track']['name']))

        playlist_info = sp.next(playlist_info)

    #sending the delete list to be displayed on the frontend
    if(del_tracks):
        songArray = []
        for song in del_tracks:
            songObj = {}
            songObj['song_uri'] = song[0]
            songObj['song_name'] = song[1]
            songArray.append(songObj)
        
        g_DICT[tid]["sp"] = sp
        g_DICT[tid]["del_tracks"] = del_tracks
        g_DICT[tid]["playlist_items"] = playlist_items
        g_DICT[tid]["playlist_uri"] = playlist_uri
        return jsonify({'songs' : songArray})
    
    songArray = []
    songObj = {}
    songObj['song_uri'] = "None"
    songObj['song_name'] = "There are no songs to be deleted, please select another playlist!"
    songArray.append(songObj)
    return jsonify({'songs' : songArray})

@app.route('/logout', methods=['GET'])
def logout():
    global g_DICT

    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        if session:
            if 'username' in session:
                app.logger.info("User logout: %s", session['username'])
            else:
                app.logger.info("User logout")

            if 'tid' in session:
                tid = session['tid']
            if 'mycache' in session:
                os.remove(session['mycache'])
            session.clear()
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))
    if tid:
        g_DICT.pop(tid)
    return redirect('/')

@app.route('/')
def root():
    username=""
    url="index.html"

    if 'username' in session:
        return redirect('/refresher')

    return redirect("index.html")

@app.route('/about', methods=['GET', 'POST'])
def about():
    username=""
    if 'username' in session:
        username = session['username']

    return render_template("about.html", username=username)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    username=""
    if 'username' in session:
        username = session['username']

    return render_template("contact.html", username=username)

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('templates', path)

if __name__ == '__main__':
    context = ('secret/certificate.crt', 'secret/private.key')

    app.run(debug=False, use_reloader=False, host=SERVER_IP, port=SERVER_PORT, threaded=True, ssl_context=context)

