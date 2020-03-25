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

from dateutil import parser


from google.auth.transport.requests import Request

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


SPOTIPY_CLIENT_ID = '71f415cec4364aa1acbf7c28b53d4f79'
SPOTIPY_CLIENT_SECRET = '53bad3d05cd948eeb8e5f7c72cf7d0db'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:8000/callback/'
SCOPE = 'user-library-read'

def home_view(request):
    context = {}

    if request.user.is_authenticated:
        user = User.objects.get(username=request.user)
        sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE)
        
        ##### for google auth ##########
        gtoken_info=''
        
        try :
            gtoken_info = eval(user.profile.gcreds)#change name
        except:
            pass    
        
        credentials, yt = '',''
        if(gtoken_info):
            exp = parser.parse(gtoken_info['expiry'])
            #print(exp)
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
            req = yt.playlists().list(part="contentDetails,snippet",maxResults=25,mine=True)
            ytlists = req.execute()
            context['ytlists'] = {}
            next_page = ytlists.get('nextPageToken')
            if not ytlists['items']:
                context['ytlists'] = {'Could not find any playlists':'Err'}#handle this
            for ytlist in ytlists['items']:
                context['ytlists'][ytlist['snippet']['title']] = {}
                req = yt.playlistItems().list(
                    part="snippet",
                    playlistId=ytlist['id'],
                    maxResults=25)
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




                

        
        


        access_token = ""
        #token_info = sp_oauth.get_cached_token()
        token_info = ""
        try:
            token_info = eval(user.profile.creds)
        except:
            pass

        if token_info:
            #print(token_info)
            if sp_oauth.is_token_expired(token_info):
                token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
                user.profile.creds = str(token_info)
                user.save()
            if token_info:
                access_token = token_info['access_token']

        if access_token:
            sp = spotipy.Spotify(access_token)
            spuser = sp.current_user()
            playlists = sp.user_playlists(spuser['id'])
            #print(playlists)
            #context['playlists'] = {}
            if not playlists['items']:
                context['playlists'] = {'Could not find any playlists':'Err'}#handle this
            for playlist in playlists['items']:
                if playlist['owner']['id'] == spuser['id']:
                    context['playlists'][playlist['name']] = {}
                    results = sp.playlist(playlist['id'], fields="tracks,next")
                    tracks = results['tracks']
                    for i, item in enumerate(tracks['items']):
                        track = item['track']
                        context['playlists'][playlist['name']][i+1] = track['name'] 
                    while tracks['next']:
                        tracks = sp.next(tracks)
                        for i, item in enumerate(tracks['items']):
                            track = item['track']
                            context['playlists'][playlist['name']][i+1] = track['name'] 

    #context['ctx'] = context
    return render(request, 'home.html', context=context)


@login_required(login_url='login')
def google(request):
    # context = {}
    # user = User.objects.get(username=request.user)
    # token_info=""
    # try:
    #     token_info = eval(user.profile.gcreds)
    # except:
    #     pass
    # #to do handle this
    # if token_info:
    #     context['creds'] = token_info
    #     context['ctx'] = context
    #     return render(request, 'home.html', context=context)

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
    # user = User.objects.get(username=request.user)
    # token_info = ""
    # try:
    #     token_info = eval(user.profile.creds)
    # except:
    #     pass
    
    # if token_info:
    #     #print(token_info)
    #     return redirect('home')#to-do handle this

    sp_oauth = oauth2.SpotifyOAuth( SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, scope=SCOPE, show_dialog=True)
    return redirect(sp_oauth.get_authorize_url())



def oauth2callback(request):

    #to do This->Note that you should do some error handling here incase its not a valid token.
    state = request.GET.get('state',None)


    state = request.GET.get('state',None)
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secret.json',
        ['https://www.googleapis.com/auth/youtube'],
        state = state)#To do handle this giving scopes error

    flow.redirect_uri = 'http://127.0.0.1:8000/oauth2callback'

    url = request.build_absolute_uri() 
    flow.fetch_token(authorization_response=url)
    credentials = flow.credentials
    #print(credentials.expiry)
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
        print('saved this :' ,token_info)
    else:
        HttpResponse("Could not fetch token go to 'home' and try again")

    return redirect('home')

# def refresh_token(request,gtoken_info):
#     user = User.objects.get(username = request.user)
    
#     credentials, yt = None,None
    
#     credentials = Credentials(token = gtoken_info['token'],
#                 refresh_token=gtoken_info['refresh_token'],
#                 token_uri=gtoken_info['token_uri'],
#                 client_id=gtoken_info['client_id'],
#                 client_secret=gtoken_info['client_secret'])
   
#     req = Request()
#     credentials.refresh(req)
#     creds = None
#     if credentials:
#         creds = {
#             'token': credentials.token,
#             'refresh_token': credentials.refresh_token,
#             'expiry': str(credentials.expiry), 
#             'token_uri': credentials.token_uri,
#             'client_id': credentials.client_id,
#             'client_secret': credentials.client_secret,
#             'scopes': credentials.scopes}

#     user.profile.gcreds = str(creds)
#     user.save()
#     return

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
        #print("Got the code")
        access_token = token_info['access_token']
    else:
        pass#important handle this

    return redirect('home')
        

@login_required(login_url='login')
def update_profile(request):#for testing ,to-do handle this
    user = User.objects.get(username=request.user)
    user.profile.creds = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit...'
    user.profile.gcreds = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit...'
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
