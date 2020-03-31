from django.contrib import admin
from django.urls import path, include
from spot.views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', home_view, name="home"),
    path('home/', home_view, name="home"),
    # path('signup/', signup_view, name="signup"),
    path('update/', scratch_creds, name="scratch"),
    # path('login/', auth_views.LoginView.as_view(template_name='ex/login.html'), name='login'),
    # path('accounts/', include('django.contrib.auth.urls')),
    path('spotify/', spotify, name='spotify'),
    path('callback/', callback, name='callback'),
    # path('google/', google, name='google'),
    # path('oauth2callback', oauth2callback, name='oauth2callback'),
    path('update_list/', update_list, name='update_list'),
    path('playlist/<str:playlist_id>', yt_playlist, name='yt_playlist'),
    path('spplaylist/<str:playlist_id>', sp_playlist, name='sp_playlist'),
    path('create', create_playlist, name='create_playlist'),
]
