from .models import *
from .forms import *
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q


def post_list(request):
    query = request.GET.get('query')
    if query:
        posts = Post.objects.filter(Q(text__icontains=query)|Q(title__icontains=query)).order_by('-date_created')
    else:
        posts = Post.objects.all().order_by('-date_created')

    return render(request, 'reddit/post_list.html',  {'posts': posts, 'form': SearchForm(initial={'query' : query})})

@login_required
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.submitter = request.user
            post.save()
            for subreddit_id in request.POST.getlist('subreddits'):
                SubRedditPost.objects.create(subreddit_id=subreddit_id, post=post)
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'reddit/post_edit.html', {'form': form, 'is_create': True})

@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post, initial={'subreddits' : post.subreddits.all()})
    return render(request, 'reddit/post_edit.html', {'form': form, 'is_create': False})


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'reddit/post_detail.html', {'post': post})



def sub_detail(request, pk):
    sub = get_object_or_404(SubReddit, pk=pk)
    return render(request, 'reddit/sub_detail.html', {'sub': sub})


@login_required
def add_comment(request, pk, parent_pk=None):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.parent_id = parent_pk
            comment.save()
        return redirect('post_detail', pk=post.pk)
    else:
        form = CommentForm()
    return render(request, 'reddit/add_comment.html', {'form': form})

@login_required
def vote(request, pk, is_upvote):
    content_obj = Votable.get_object(pk)
    content_obj.toggle_vote(request.user, UserVote.UP_VOTE if is_upvote else UserVote.DOWN_VOTE)

    if isinstance(content_obj, Comment): post = content_obj.post
    else: post = content_obj

    return redirect('post_detail', pk=post.pk)