from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect
)

from yatube.settings import POSTS_PER_PAGE, CACHE_TIME
from .forms import PostForm, CommentForm
from .models import Follow, Post, Group, User


def get_page_obj(posts, request):
    return Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get('page'))


@cache_page(CACHE_TIME, key_prefix='index_page')
def index(request):
    return render(request, 'posts/index.html', {
        'page_obj': get_page_obj(Post.objects.all(), request)
    })


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    return render(request, 'posts/group_list.html', {
        'group': group,
        'page_obj': get_page_obj(group.posts.all(), request)
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    return render(request, 'posts/profile.html', {
        'author': author,
        'page_obj': get_page_obj(author.posts.all(), request),
        'following': request.user.is_authenticated and author.following.filter(
            user=request.user
        ).exists()
    })


def post_detail(request, post_id):
    return render(request, 'posts/post_detail.html', {
        'post': get_object_or_404(Post, pk=post_id),
        'form': CommentForm(request.POST or None)
    })


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {
            'form': form,
            'is_edit': False
        })
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=request.user)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if not form.is_valid():
        return render(
            request,
            'posts/create_post.html',
            {'form': form, 'is_edit': True, 'post_id': post.id}
        )
    form.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    return render(request, 'posts/follow.html', {
        'page_obj': get_page_obj(
            Post.objects.filter(author__following__user=request.user),
            request
        ),
    })


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if (
        (author != request.user)
        and not request.user.follower.filter(author=author).exists()
    ):
        Follow.objects.create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    get_object_or_404(
        Follow,
        user=request.user,
        author=User.objects.get(username=username)
    ).delete()
    return redirect('posts:profile', username=username)
