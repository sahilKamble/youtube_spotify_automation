from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    creds = models.CharField(max_length=999, blank=True, null=True)
    curr_yt_playlistid = models.CharField(max_length=99, null=True)
    curr_sp_playlistid = models.CharField(max_length=99, null=True)
    
    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class YtTrack(models.Model):
    vidid = models.CharField(max_length=99, null=True)
    sp_playlistid = models.CharField(max_length=99, null=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return self.vidid

class SpTrack(models.Model):
    trackid = models.CharField(max_length=99, null=True)
    yt_playlistid = models.CharField(max_length=99, null=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
            return self.trackid