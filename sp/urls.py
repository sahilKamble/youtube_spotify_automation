from django.contrib import admin
from django.urls import path, include
from spot.views import home_view, signup_view, update_profile, spotify, callback, google, oauth2callback
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name="home"),
    path('home/', home_view, name="home"),
    path('signup/', signup_view, name="signup"),
    path('update/', update_profile, name="update"),
    #path('logout/', logout_view, name ="logout1"),
    #path('login/', login_view, name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='ex/login.html'), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('spotify/', spotify, name='spotify'),
    path('callback/', callback, name='callback'),
    path('google/', google, name='google'),
    path('oauth2callback', oauth2callback, name='oauth2callback'),
]
