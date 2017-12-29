import json
from flask import Flask, request, redirect, g, render_template, session
from werkzeug.utils import secure_filename
import requests
import base64
import urllib
import os
#from app import *

app = Flask(__name__)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

#  Client Keys
CLIENT_ID = "2fddf269c1e5483d92c3aa0ff4aafcaf"
CLIENT_SECRET = "e0a8951722994ff7804e58fd4017333c"

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)
access_token = ""
auth_token = ""

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 8080
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-modify-public playlist-modify-private"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

user_name = ""
authorization_header = ""
user_profile_api_endpoint = ""
profile_response = ""
profile_data = ""

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}

def displayName(data):
    display_name = ""
    if data['display_name']:
        display_name = data['display_name']
    else:
        display_name = data['id']
    return display_name

def profilePic(data):
    profile_pic = ""
    if data['images'][0]['url']:
        profile_pic = data['images'][0]['url']
    else:
        profile_pic = "../static/img/profile.jpg"
    return profile_pic

def process_file(filename):
    #Only XML files
    base, extension = os.path.splitext(filename)
    if extension != ".xml":
        print "Wrong file type. XML files only."
        return
    else:
        f = open(filename, "r")
from bs4 import BeautifulSoup
import spotipy
import spotipy.util as util
import spotipy.oauth2 as oauth2
import os
import sys
import time
import json
# Note: Change oauth2.py method back to normal after web app is up

class playlistParse:

    def __init__(self, file):
        self.trackList = {}
        self.playlistName = ""
        self.fileName = file
        self.handler = open(self.fileName).read()
        self.soup = BeautifulSoup(self.handler, "xml")
        self.soup.prettify()

    def getPlaylistName(self):
        return self.playlistName

    def getTracklist(self):
        return self.trackList

    def createTracklist(self):
        for item in self.soup.find_all('key'):
            if item.contents[0] == "Name" and item.find_next_sibling("key").contents[0] == "Artist":
                #Compound IF is to filter for the name of the playlist that shows up at the end
                trackName = item.find_next_sibling("string").contents[0]

            if item.contents[0] == "Name" and item.find_next_sibling("key").contents[0] != "Artist":
                self.playlistName = item.find_next_sibling("string").contents[0]

            if item.contents[0] == "Artist":
                trackArtist = item.find_next_sibling("string").contents[0]

                self.trackList[trackName.encode("utf-8")] = trackArtist.encode("utf-8")

class Spotify:

    '''os.environ['SPOTIPY_CLIENT_ID'] = "2fddf269c1e5483d92c3aa0ff4aafcaf"
    os.environ['SPOTIPY_CLIENT_SECRET'] = "e0a8951722994ff7804e58fd4017333c"
    #os.environ['SPOTIPY_REDIRECT_URI'] = 'http://localhost/'
    os.environ['SPOTIPY_REDIRECT_URI'] = "http://127.0.0.1:8080/callback/q"
    '''
    def __init__(self, access_token, user_name):
        self.myUserName = user_name
        self.token = access_token
        self.myPlaylists = {}
        self.notFound = []
        self.addedTracks = {}
        self.cantFind= {}
        self.processed = 0

        if self.token:
            self.sp = spotipy.Spotify(auth=self.token)
            self.sp.trace = False
        else:
            print("Can't get token for ", self.myUserName)

    def currentUser(self):
        user  = self.sp.user(self.myUserName)
        print user

    def currentPlaylists(self):
        """
        Returns all playlists in a dict of form {playlist name: playlist id}
        """
        playlists = self.sp.user_playlists(self.myUserName)

        for playlist in playlists['items']:
            self.myPlaylists[playlist['name']] = playlist['id']

        return playlists

    def createPlaylist(self, playlistName):

        if playlistName in self.myPlaylists.keys():
            print("Playlist '" + playlistName + "' already exists.")
            sys.exit(0)

        else:
            self.sp.user_playlist_create(self.myUserName, playlistName)
            playlists = self.currentPlaylists()
            for playlist in playlists['items']:
                if playlist['name'] == playlistName:
                    self.myPlaylists[playlistName] = playlist  ['id']

    def addTracks(self, playlistName, trackList):
        songsToAdd = []
        failedToFind = {}

        for track, artist in trackList.items():
            searchString = track + " " + artist
            result = self.sp.search(searchString, type='track', limit=1)

            if len(result["tracks"]["items"]) > 0:
                album_name = result["tracks"]["items"][0]["album"]["name"]
                track_artist_pair = (track.decode('utf-8'), artist.decode('utf-8'))
                self.addedTracks[track_artist_pair] = album_name
                self.processed = len(self.addedTracks)
                songsToAdd.append(result["tracks"]["items"][0]["id"])
            else:

                failedToFind[track] = artist
                #print "'" + track  + "' by: " + artist + " not found. Trying again."

        toAdd = self.tryAgainTracks(failedToFind)

        songsToAdd.extend(toAdd)

        count = 0
        for song in songsToAdd:
            # Note to self: I wrapped "song" in a list for a reason. It's not a typo.
            self.sp.user_playlist_add_tracks(self.myUserName, self.myPlaylists[playlistName], [song])
            count += 1

        print "Songs processed: " + str(count)

    def tryAgainTracks(self, failedTracks):
        toAdd = []
        noHope = []

        for track,artist in failedTracks.items():
            baseTrackname = track.split("(", 1)[0]
            searchString = baseTrackname + " " + artist
            result = self.sp.search(searchString, type="track", limit=1)

            if len(result["tracks"]["items"]) > 0:
                album_name = result["tracks"]["items"][0]["album"]["name"]
                track_artist_pair = (track.decode('utf-8'), artist.decode('utf-8'))

                toAdd.append(result["tracks"]["items"][0]["id"])
                self.addedTracks[track_artist_pair] = album_name

                #print("\nWe couldn't find '" + track + "' but we found and added '" + baseTrackname + "'")
            else:
                print track
                self.cantFind[track.decode('utf-8')] = artist.decode('utf-8')
                noHope.append(searchString)


        #print "No match: " + str(len(noHope))
        self.notFound = noHope

        return toAdd


'''if __name__ == '__main__':
    p = playlistParse()
    s = Spotify()

    p.createTracklist()

    playlistName = p.playlistName
    print playlistName

    trackList = p.trackList
    print len(trackList)

    s.currentPlaylists()
    s.createPlaylist(playlistName)
    print s.myPlaylists[playlistName]
    s.addTracks(playlistName, trackList)

'''
@app.route("/")
def index():
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key, urllib.quote(val)) for key, val in auth_query_parameters.iteritems()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)

@app.route("/callback/q")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    global access_token
    global auth_token
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI
    }
    base64encoded = base64.b64encode("{}:{}".format(CLIENT_ID, CLIENT_SECRET))
    headers = {"Authorization": "Basic {}".format(base64encoded)}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    # Auth Step 6: Use the access token to access Spotify API

    global authorization_header
    global user_profile_api_endpoint
    global profile_response
    global profile_data
    global user_name

    authorization_header = {"Authorization": "Bearer {}".format(access_token)}
    user_profile_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
    profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
    profile_data = json.loads(profile_response.text)

    user_name = profile_data['id']


    global DISPLAY_NAME
    global PROFILE_PIC
    DISPLAY_NAME = displayName(profile_data)
    PROFILE_PIC = profilePic(profile_data)
    '''
    playlist_api_endpoint = "{}/playlists".format(profile_data["href"])
    playlists_response = requests.get(playlist_api_endpoint, headers=authorization_header)
    playlist_data = json.loads(playlists_response.text)
    '''
    #for item in playlist_data['items']:
    #    print item['images'][1]['url']

    '''
    target = os.path.join(APP_ROOT, "files/")
    print target

    if not os.path.isdir(target):
        os.mkdir(target)

    for file in request.files.getlist("file"):
        filename = file.filename
        destination = "/".join([target, filename])
        print destination
    '''
    return render_template("index.html", display_name = DISPLAY_NAME, profile_pic = PROFILE_PIC)


@app.route('/upload', methods = ['GET','POST'])
def upload():
    playlist_img = ""
    num_tracks = 0
    display_failed_tracks = "display:none;"

    target = os.path.join(APP_ROOT, "files/")
    #print target

    if not os.path.isdir(target):
        os.mkdir(target)

    if len(request.files.getlist("file")) < 1:
        print "File was not uploaded"
        sys.exit(2)
    else:
        file = request.files.getlist("file")[0]
        filename = file.filename
        destination = "/".join([target, filename])
        file.save(destination)


        p = playlistParse(destination)
        p.createTracklist()
        playlistName = p.playlistName

        trackList = p.trackList

        s= Spotify(access_token, user_name)
        s.currentPlaylists()
        s.createPlaylist(playlistName)
        #print s.myPlaylists[playlistName]

        s.addTracks(playlistName, trackList)
        trackList = s.addedTracks
        totalTracks = len(trackList)

        failedTracks = s.notFound
        #print failedTracks

        playlist_api_endpoint = "{}/playlists".format(profile_data["href"])
        playlists_response = requests.get(playlist_api_endpoint, headers=authorization_header)
        playlist_data = json.loads(playlists_response.text)

        for playlist in playlist_data['items']:
            if playlist['name'] == playlistName:
                num_tracks = int(playlist['tracks']['total'])

                if len(playlist['images']) != 0 :
                    playlist_img = playlist['images'][0]['url']
                else:
                    playlist_img = "../static/img/empty_playlist_cover.png"


        if len(failedTracks) > 0:
            display_failed_tracks = "display:block;"

    return render_template("upload.html", display_name = DISPLAY_NAME, profile_pic = PROFILE_PIC,
                           playlist_img = playlist_img,
                           playlist_name = playlistName,
                           num_tracks = num_tracks,
                           trackList = trackList,
                           display_failed_tracks = display_failed_tracks,
                           num_failed_tracks = len(failedTracks),
                           failed_trackList = s.cantFind
                           )

'''
@app.route("/upload", methods = ["POST"])
def upload():
    target = os.path.join(APP_ROOT, "files/")
    print target

    if not os.path.isdir(target):
        os.mkdir(target)

    for file in request.files.getlist("file"):
        print file
        filename = file.filename
        destination = "/".join([target, filename])
        print destination

        #Only XML files
        base, extension = os.path.splitext(destination)
        if extension != ".xml":
            return "Wrong file type. XML files only. Exiting."
        else:
            file.save(destination)

        #f= open(destination, "r")

        p = playlistParse(destination)
        s = Spotify()

        p.createTracklist()

        tracks = []
        for song in p.trackList:
            tracks.append(song.decode('utf-8'))

        s.currentPlaylists()
        s.createPlaylist(p.playlistName)
        s.addTracks(p.playlistName,p.trackList)

    return render_template("display.html",
                           playlistName = p.playlistName,
                           trackList = tracks,
                           notFound = s.notFound)


'''

if __name__ == "__main__":
    app.run(debug=True, port=PORT)
    #process_file("Anglais.txt")