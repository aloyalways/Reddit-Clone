from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models.signals import post_save, post_delete
from django.conf import settings
import uuid
from django.db.models import F
from django.dispatch import receiver

class BaseModel(models.Model):
    eid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta: abstract = True

    # Helper method, so that we don't have to do the existence check every time.
    @classmethod
    def get_or_none(cls, **kwargs):
        try:
            return cls.objects.get(**kwargs)
        except cls.DoesNotExist:
            return None

class SubReddit(BaseModel):
    name = models.CharField(max_length=200)
    posts = models.ManyToManyField('Post', related_name='subreddits', blank=True, through='SubRedditPost')
    cover_image_url = models.URLField('Cover Image URL', max_length=200, blank=True, null=True )
    moderators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='subreddits_moderated')

    def __str__(self):
        return self.name

class SubRedditPost(BaseModel):
    subreddit = models.ForeignKey('SubReddit', related_name='posts_set', on_delete=models.CASCADE)
    post = models.ForeignKey('Post', related_name='subreddits_set', on_delete=models.CASCADE)

    class Meta: unique_together = ['subreddit', 'post']

class Votable(BaseModel):
    upvote_count = models.PositiveIntegerField(default=0)
    downvote_count = models.PositiveIntegerField(default=0)
    class Meta: abstract = True

    def toggle_vote(self, voter, vote_type):
        uv = UserVote.get_or_none(voter=voter, object_id=self.eid)

        if uv:
            # Case 1.1: Cancel existing upvote/downvote (i.e. toggle)
            if uv.vote_type == vote_type:
                uv.delete()
            # Case 1.2: You're either switching from upvote to downvote, or from downvote to upvote
            else:
                uv.vote_type = vote_type
                uv.save()
        # Case 2: User has not voted on this object before
        else:
            UserVote.objects.create(voter=voter, content_object=self, vote_type=vote_type)

    def _change_vote_count(self, vote_type, delta):
        self.refresh_from_db()
        if vote_type == UserVote.UP_VOTE:
            self.upvote_count = F('upvote_count') + delta
        elif vote_type == UserVote.DOWN_VOTE:
            self.downvote_count = F('downvote_count') + delta
        self.save()
        self.refresh_from_db()

    def change_upvote_count(self, delta):
        self._change_vote_count(UserVote.UP_VOTE, delta)
    def change_downvote_count(self, delta):
        self._change_vote_count(UserVote.DOWN_VOTE, delta)

    def get_user_vote(self, user):
        if not user or not user.is_authenticated: return None

        uv = UserVote.get_or_none(voter=user, object_id=self.eid)
        if not uv: return None
        if uv.vote_type == UserVote.UP_VOTE: return 1
        else: return -1

    def get_score(self):
        return self.upvote_count - self.downvote_count

    @staticmethod
    def get_object(eid):
        post = Post.get_or_none(eid=eid)
        if post: return post

        comment = Comment.get_or_none(eid=eid)
        if comment: return comment


class Post(Votable):
    title = models.CharField(max_length=200)
    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='posts_submitted', on_delete=models.CASCADE)
    url = models.URLField('URL', max_length=200, null=True, blank=True)
    text = models.TextField(blank=True, null=True)
    comment_count = models.PositiveIntegerField(default=0)

    def children(self):
        return self.comments.filter(parent=None)

    def __str__(self):
        return str(self.eid) + ": " + self.title

class Comment(Votable):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='comments_authored', on_delete=models.CASCADE)
    text = models.TextField()
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.eid) + ": " + self.text


class UserVote(BaseModel):
    UP_VOTE = 'U'
    DOWN_VOTE = 'D'
    VOTE_TYPE = (
        (UP_VOTE, 'Up Vote'),
        (DOWN_VOTE, 'Down Vote')
    )

    voter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='votes', on_delete=models.CASCADE)

    #Generic Foreign Key config
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    vote_type = models.CharField(max_length=1, choices=VOTE_TYPE)

    class Meta: unique_together = ['voter', 'object_id', 'content_type']


@receiver(post_save, sender=UserVote, dispatch_uid="user_voted")
def user_voted(sender, instance, **kwargs):
    created = kwargs.pop('created')
    content_obj = instance.content_object

    # The user is voting for the first time
    if created:
        if instance.vote_type == UserVote.UP_VOTE: content_obj.change_upvote_count(1)
        else: content_obj.change_downvote_count(1)

    # The user must have switched votes
    else:
        # The previous vote was a downvote, but now is switched to an upvote
        if instance.vote_type == UserVote.UP_VOTE:
            content_obj.change_upvote_count(1)
            content_obj.change_downvote_count(-1)
        else:
            content_obj.change_upvote_count(-1)
            content_obj.change_downvote_count(1)

@receiver(post_delete, sender=UserVote, dispatch_uid="user_vote_deleted")
def user_vote_deleted(sender, instance, **kwargs):
    content_obj = instance.content_object

    if instance.vote_type == UserVote.UP_VOTE: content_obj.change_upvote_count(-1)
    else: content_obj.change_downvote_count(-1)


@receiver(post_save, sender=Comment, dispatch_uid="comment_added")
def comment_added(sender, instance, **kwargs):
    created = kwargs.pop('created')
    post = instance.post

    if created:
        post.comment_count = F('comment_count') + 1
        post.save()