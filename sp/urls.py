from django.contrib import admin
from django.urls import path, include
# from spotify_example.spot.views import *
from spot.views import *
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', home_view, name="home"),
    path('home/', home_view, name="home"),
    path('scratch/', scratch_creds, name="scratch"),
    path('spotify/', spotify, name='spotify'),
    path('callback/', callback, name='callback'),
    path('update_list/', update_list, name='update_list'),
    path('update_sp_list/', update_sp_list, name='update_sp_list'),
    path('playlist/<str:playlist_id>', yt_playlist, name='yt_playlist'),
    path('spplaylist/<str:playlist_id>', sp_playlist, name='sp_playlist'),
    path('create', create_playlist, name='create_playlist'),
    path('create_sp', create_sp_playlist, name='create_sp_playlist'),
]
