from django import forms
from .models import *

class PostForm(forms.ModelForm):
    subreddits = forms.ModelMultipleChoiceField(queryset=SubReddit.objects.all())

    class Meta:
        model = Post
        fields = ('title', 'text', 'url', 'subreddits')

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)

class SearchForm(forms.Form):
    query = forms.CharField(label='Query', required=False)