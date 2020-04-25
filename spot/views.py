from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
import spotipy
from spotipy import oauth2
import google.oauth2.credentials
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from allauth.socialaccount.models import SocialToken, SocialApp
from dateutil import parser
import youtube_dl

from .models import YtTrack,SpTrack


TOKEN_URI = 'https://oauth2.googleapis.com/token'
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/userinfo.profile email']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

SPOTIPY_CLIENT_ID = settings.SPOTIPY_CLIENT_ID
SPOTIPY_CLIENT_SECRET = settings.SPOTIPY_CLIENT_SECRET
SPOTIPY_REDIRECT_URI = settings.SPOTIPY_REDIRECT_URI
SCOPE = settings.SPOTIPY_SCOPE

def home_view(request):
    context = {}

    if request.user.is_authenticated:
        user = User.objects.get(username=request.user)
        
        gtoken_info = None
        credentials = None
        yt = None

        if SocialToken.objects.filter(account__user=user,account__provider='google').exists():
            credentials = get_credentials(user)
        
        if credentials:
            yt = build(API_SERVICE_NAME, API_VERSION, credentials = credentials)
            context['ytlists'] = {}
            req = yt.playlists().list(part="contentDetails,snippet",maxResults=25,mine=True)
            ytlists = req.execute()
            next_page = ytlists.get('nextPageToken')
            if not ytlists['items']:
                context['ytlists'] =  {'None':
                    {'name':'Could not find any playlist'}}
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
            if user.profile.curr_yt_playlistid in context['ytlists']:
                context['yt_tracking'] = context['ytlists'][user.profile.curr_yt_playlistid]['name']

        access_token = None
        token_info = None

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
                context['playlists'] =  {'None':
                    {'name':'Could not find any playlist'}}
            for playlist in playlists['items']:
                if playlist['owner']['id'] == spuser['id']:
                    context['playlists'][playlist['id']] = {'name':playlist['name']}
                    results = sp.playlist(playlist['id'], fields="tracks,next")
                    tracks = results['tracks']
                    context['playlists'][playlist['id']]['tracks'] = []
                    for item in tracks['items'] :
                        track = item['track']
                        context['playlists'][playlist['id']]['tracks'].append(track['name']) 

            if user.profile.curr_sp_playlistid in context['playlists']:
                context['sp_tracking'] = context['playlists'][user.profile.curr_sp_playlistid]['name']

    return render(request, 'home.html', context=context)

def yt_playlist(request, playlist_id):
    if playlist_id == 'None':
        return redirect('home')
    user = User.objects.get(username=request.user)
    user.profile.curr_yt_playlistid = playlist_id
    user.save()
    return redirect('home')

def sp_playlist(request, playlist_id):
    if playlist_id == 'None':
        return redirect('home')
    user = User.objects.get(username=request.user)
    user.profile.curr_sp_playlistid = playlist_id
    user.save()
    return redirect('home')

def create_playlist(request):
    if request.method == "POST":
        yt = build(API_SERVICE_NAME, API_VERSION, credentials = credentials)
        title =  request.POST['title']
        description = request.POST['description']

        req = yt.playlists().insert(
            part="snippet",
            body={
            "snippet": {
                "title": title,
                "description": description
                }
            }
        )
        
        res = req.execute()
        playlistid = res["id"]
        user = User.objects.get(username=request.user)
        credentials = get_credentials(user)
        user.profile.ytid = playlistid
        user.save()
        return redirect('home')

def create_sp_playlist(request):
    user = User.objects.get(username=request.user)
    if user.profile.creds:
        token_info = eval(user.profile.creds)
        sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE)
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            user.profile.creds = str(token_info)
            user.save()
        
        access_token = token_info['access_token']
        sp = spotipy.Spotify(access_token)
        spuser = sp.current_user()
        if request.method == "POST":
            title =  request.POST['title']
            description = request.POST['description']
            sp.user_playlist_create(user=spuser['id'],name=title,
                description=description)
    return redirect('home')




@login_required
def spotify(request):
    sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE, show_dialog=True)
    return redirect(sp_oauth.get_authorize_url())


@login_required
def callback(request):
    context = {}
    user = User.objects.get(username=request.user)
    sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE)
    url = request.build_absolute_uri() 
    code = sp_oauth.parse_response_code(str(url))
    if code is None:
        return redirect('home')
    token_info = sp_oauth.get_access_token(code, check_cache=False)
    context['token_info'] = token_info
    user.profile.creds = str(token_info)
    user.save()
    access_token = token_info['access_token']
    return redirect('home')

@login_required
def scratch_creds(request):
    if request.method == "POST":
        user = User.objects.get(username=request.user)
        user.profile.creds = None
        user.save()
        return redirect('home') 
    return render(request, "scratch.html")


@login_required
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

    credentials = get_credentials(user)
    yt = build(API_SERVICE_NAME, API_VERSION, credentials = credentials)
    req = yt.playlistItems().list(
        part="snippet",
        playlistId=user.profile.curr_yt_playlistid,
        maxResults=25)
    res = req.execute()
    sp_new_traks = []
    for track in res['items']:
        if not user.profile.yttrack_set.filter(
            vidid=track['snippet']['resourceId']['videoId'],
            sp_playlistid=user.profile.curr_sp_playlistid).exists() :

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
                sp_new_traks.append(spres['tracks']['items'][0]['id'])
                YtTrack.objects.create(vidid=track['snippet']['resourceId']['videoId'], sp_playlistid=user.profile.curr_sp_playlistid, profile=user.profile)
            

    
    spuser = sp.current_user()
    if len(sp_new_traks) > 0:
        sp.user_playlist_add_tracks(playlist_id=user.profile.curr_sp_playlistid,user=spuser['id'],tracks=sp_new_traks)

    return redirect('home')

def update_sp_list(request):
    user = User.objects.get(username=request.user)

    sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE)
    token_info = eval(user.profile.creds)
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        user.profile.creds = str(token_info)
        user.save()

    access_token = token_info['access_token']
    sp = spotipy.Spotify(access_token)
    credentials = get_credentials(user)
    yt = build(API_SERVICE_NAME, API_VERSION, credentials = credentials)

    yt_new_tracks = {}
    sp = spotipy.Spotify(access_token)
    spuser = sp.current_user()
    res = sp.playlist_tracks(user.profile.curr_sp_playlistid,fields="items(track(name,id))")
    
    for track in res['items']:
        if not user.profile.sptrack_set.filter(trackid=track['track']['id'],yt_playlistid=user.profile.curr_sp_playlistid).exists() :
                req = yt.search().list(
                    part="snippet",
                    maxResults=1,
                    q=track['track']['name'],
                    type="video",
                    videoCategoryId="10"
                )
                res = req.execute()
                if len(res['items']) > 0:    
                    yt.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": user.profile.curr_yt_playlistid,
                                "resourceId": res['items'][0]['id'],
                            }
                        }
                    ).execute()
                    SpTrack.objects.create(trackid=track['track']['id'], yt_playlistid=user.profile.curr_yt_playlistid, profile=user.profile)    
    return redirect('home')


def get_credentials(user):
    st = SocialToken.objects.get(account__user=user,account__provider='google')
    sa = SocialApp.objects.filter(provider='google').first()
    credentials = Credentials(token = st.token ,
        refresh_token = st.token_secret,
        token_uri = TOKEN_URI,
        client_id = sa.client_id,
        client_secret = sa.secret)
    credentials.expiry = st.expires_at.replace(tzinfo=None)
    if credentials.expired :
        req = Request()
        credentials.refresh(req)
        st.token = credentials.token
        st.token_secret = credentials.refresh_token
        st.save()
    return credentials