from django.contrib import admin
from .models import *

admin.site.register(Post)
admin.site.register(SubReddit)
admin.site.register(Comment)
admin.site.register(UserVote)
admin.site.register(SubRedditPost)