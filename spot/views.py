from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect
from django.http import HttpResponse
import spotipy
from spotipy import oauth2
import google.oauth2.credentials
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from dateutil import parser
import youtube_dl

from .models import YtTrack

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

SPOTIPY_CLIENT_ID = '71f415cec4364aa1acbf7c28b53d4f79'
SPOTIPY_CLIENT_SECRET = '53bad3d05cd948eeb8e5f7c72cf7d0db'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:8000/callback/'
SCOPE = 'playlist-modify-public,playlist-modify-private'

def home_view(request):
    context = {}

    if request.user.is_authenticated:
        user = User.objects.get(username=request.user)
        
        gtoken_info = None
        credentials = None
        yt = None
        #make all this a seperate task
        if user.profile.gcreds:
            gtoken_info = eval(user.profile.gcreds)#change name#Handle this
            exp = parser.parse(gtoken_info['expiry'])
            credentials = Credentials(token = gtoken_info['token'],
                refresh_token=gtoken_info['refresh_token'],
                token_uri=gtoken_info['token_uri'],
                client_id=gtoken_info['client_id'],
                client_secret=gtoken_info['client_secret'])
            credentials.expiry = exp
            if credentials.expired:
                req = Request()
                credentials.refresh(req)
                creds = None
                creds = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'expiry': str(credentials.expiry), 
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes}
                user.profile.gcreds = str(creds)
                user.save()
            yt = build(API_SERVICE_NAME, API_VERSION, credentials = credentials)
        
        if yt:
            context['ytlists'] = {}
            req = yt.playlists().list(part="contentDetails,snippet",maxResults=25,mine=True)
            ytlists = req.execute()
            next_page = ytlists.get('nextPageToken')
            if not ytlists['items']:
                context['ytlists'] = {'Could not find any playlists':'Err'}#handle this
            for ytlist in ytlists['items']:
                context['ytlists'][ytlist['id']] = {'name':ytlist['snippet']['title']}
                req = yt.playlistItems().list(
                    part="snippet",
                    playlistId=ytlist['id'],
                    maxResults=25)
                res = req.execute()
                nextVideoPage = res.get('nextPageToken')
                context['ytlists'][ytlist['id']]['tracks'] = []
                for item in res['items']:
                    context['ytlists'][ytlist['id']]['tracks'].append(item['snippet']['title'])
                while nextVideoPage:
                    req = yt.playlistItems().list(
                        part="snippet",
                        playlistId=ytlist['id'],
                        pageToken=nextVideoPage,
                        maxResults=25)
                    res = req.execute()
                    nextVideoPage = res.get('nextPageToken')
                    for item in res['items']:
                        context['ytlists'][ytlist['id']]['tracks'].append(item['snippet']['title'])

            while(next_page):
                req = yt.playlists().list(part="contentDetails,snippet",
                        maxResults=25,
                        mine=True,
                        pageToken=next_page)
                ytlists = req.execute()
                next_page = ytlists.get('nextPageToken')
                for ytlist in ytlists['items']:
                    context['ytlists'][ytlist['snippet']['title']] = {}
                    req = yt.playlistItems().list(
                        part="snippet",
                        playlistId=ytlist['id'])
                    res = req.execute()
                    nextVideoPage = res.get('nextPageToken')
                    i = 0
                    for item in res['items']:
                        i += 1
                        context['ytlists'][ytlist['snippet']['title']][i] = item['snippet']['title']
                    while nextVideoPage:
                        req = yt.playlistItems().list(
                            part="snippet",
                            playlistId=ytlist['id'],
                            pageToken=nextVideoPage,
                            maxResults=25)
                        res = req.execute()
                        nextVideoPage = res.get('nextPageToken')
                        for item in res['items']:
                            i += 1
                            context['ytlists'][ytlist['snippet']['title']][i] = item['snippet']['title']
            if user.profile.ytid in context['ytlists']:
                context['yt_tracking'] = context['ytlists'][user.profile.ytid]['name']

        access_token = None
        token_info = None

        # make all tis a seperate task
        if user.profile.creds:
            token_info = eval(user.profile.creds)
            sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE)
            if sp_oauth.is_token_expired(token_info):
                token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
                user.profile.creds = str(token_info)
                user.save()
            if token_info:
                access_token = token_info['access_token']

        if access_token:
            context['playlists'] = {}
            sp = spotipy.Spotify(access_token)
            spuser = sp.current_user()
            playlists = sp.user_playlists(spuser['id'])
            context['playlists'] = {}
            if not playlists['items']:
                context['playlists'] = {'Could not find any playlists':'Err'}#handle this
            for playlist in playlists['items']:
                context['playlists'][playlist['id']] = {'name':playlist['name']}
                results = sp.playlist(playlist['id'], fields="tracks,next")
                tracks = results['tracks']
                context['playlists'][playlist['id']]['tracks'] = []
                for item in tracks['items']:
                    track = item['track']
                    context['playlists'][playlist['id']]['tracks'].append(track['name']) 
                while tracks['next']:
                    tracks = sp.next(tracks)
                    for item in tracks['items']:
                        track = item['track']
                        context['playlists'][playlist['id']]['tracks'].append(track['name'])
            if user.profile.spid in context['playlists']:
                context['sp_tracking'] = context['playlists'][user.profile.spid]['name']

    #context['ctx'] = context
    # context['id'] = iter(context['id'])
    return render(request, 'home.html', context=context)

def yt_playlist(request, playlist_id):
    user = User.objects.get(username=request.user)
    user.profile.ytid = playlist_id
    user.save()
    return redirect('home')

def sp_playlist(request, playlist_id):
    user = User.objects.get(username=request.user)
    user.profile.spid = playlist_id
    user.save()
    return redirect('home')

def create_playlist(request):
    user = User.objects.get(username=request.user)
    
    if user.profile.gcreds:
        gtoken_info = eval(user.profile.gcreds)
        exp = parser.parse(gtoken_info['expiry'])
        credentials = Credentials(token = gtoken_info['token'],
            refresh_token=gtoken_info['refresh_token'],
            token_uri=gtoken_info['token_uri'],
            client_id=gtoken_info['client_id'],
            client_secret=gtoken_info['client_secret'])
        yt = build(API_SERVICE_NAME, API_VERSION, credentials = credentials)
        
        req = yt.playlists().insert(
            part="snippet",
            body={
            "snippet": {
                "title": "test",
                "description": "Playlist created by spotify automation app, add your songs here"
                }
            }
        )
        response = req.execute()
        id = response["id"]
        user.profile.playlistid = id
        user.save()

        return redirect('home')

@login_required(login_url='login')
def google(request):
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
    'client_secret.json',
    ['https://www.googleapis.com/auth/youtube'])

    flow.redirect_uri = 'http://127.0.0.1:8000/oauth2callback'

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    return redirect(authorization_url)

@login_required(login_url='login')
def spotify(request):
    sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE, show_dialog=True)
    return redirect(sp_oauth.get_authorize_url())

def oauth2callback(request):

    #to do This->Note that you should do some error handling here incase its not a valid token.
    state = request.GET.get('state',None)
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secret.json',
        ['https://www.googleapis.com/auth/youtube'],
        state = state)#To do handle this giving scopes error

    flow.redirect_uri = 'http://127.0.0.1:8000/oauth2callback'

    url = request.build_absolute_uri() 
    flow.fetch_token(authorization_response=url)
    credentials = flow.credentials
    creds = dict()
    if credentials:
        creds = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'expiry': str(credentials.expiry), 
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

        user = User.objects.get(username=request.user)
        user.profile.gcreds = str(creds)
        user.save()

        token_info = eval(user.profile.gcreds)
    else:
        HttpResponse("Could not fetch token go to 'home' and try again")

    return redirect('home')


@login_required(login_url='login')
def callback(request):
    context = {}
    user = User.objects.get(username=request.user)
    sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE)#to-do handle this better, make object global??
    url = request.build_absolute_uri() 
    code = sp_oauth.parse_response_code(str(url))
    if code:
        token_info = sp_oauth.get_access_token(code, check_cache=False)
        context['token_info'] = token_info
        user.profile.creds = str(token_info)
        user.save()
        access_token = token_info['access_token']
    else:
        pass#important handle this

    return redirect('home')

@login_required(login_url='login')
def update_profile(request):#for testing ,to-do handle this
    user = User.objects.get(username=request.user)
    user.profile.creds = None
    user.profile.gcreds = None
    user.save()
    return redirect('home')

def signup_view(request):
    form = UserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        login(request, user)
        return redirect('home')
    return render(request, 'signup.html', {'form': form})

@login_required(login_url='login')
def update_list(request):
    user = User.objects.get(username=request.user)

    sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE)
    token_info = eval(user.profile.creds)

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        user.profile.creds = str(token_info)
        user.save()

    access_token = token_info['access_token']

    sp = spotipy.Spotify(access_token)
    spid = []

    gtoken_info = eval(user.profile.gcreds)
    exp = parser.parse(gtoken_info['expiry'])
    gcredentials = Credentials(token = gtoken_info['token'],
        refresh_token=gtoken_info['refresh_token'],
        token_uri=gtoken_info['token_uri'],
        client_id=gtoken_info['client_id'],
        client_secret=gtoken_info['client_secret'])
    gcredentials.expiry = exp
    if gcredentials.expired:
        req = Request()
        gcredentials.refresh(req)
        creds = None
        creds = {
            'token': gcredentials.token,
            'refresh_token': gcredentials.refresh_token,
            'expiry': str(gcredentials.expiry), 
            'token_uri': gcredentials.token_uri,
            'client_id': gcredentials.client_id,
            'client_secret': gcredentials.client_secret,
            'scopes': gcredentials.scopes}
        user.profile.gcreds = str(creds)
        user.save()
    yt = build(API_SERVICE_NAME, API_VERSION, credentials = gcredentials)
    req = yt.playlistItems().list(
        part="snippet",
        playlistId=user.profile.ytid,
        maxResults=25)
    res = req.execute()
    newtracks = list()

    for track in res['items']:
        if user.profile.yttrack_set.filter(vidid=track['snippet']['resourceId']['videoId'],spid=user.profile.spid).exists() :
            pass
        else:
            newtrack = track['snippet']['resourceId']['videoId']
            youtube_url = "https://www.youtube.com/watch?v={}".format(newtrack)
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]
            spres = None 
            if song_name :
                spres = sp.search(q=song_name,limit=1)
            else :
                name = track['snippet']['title']
                spres = sp.search(q=name,limit=1)

            if spres and len(spres['tracks']['items']) > 0 :
                spid.append(spres['tracks']['items'][0]['id'])
                YtTrack.objects.create(vidid=track['snippet']['resourceId']['videoId'], spid=user.profile.spid, profile=user.profile)
            

    
    spuser = sp.current_user()
    if len(spid) > 0:
        sp.user_playlist_add_tracks(playlist_id=user.profile.spid,user=spuser['id'],tracks=spid)

    return redirect('home')
