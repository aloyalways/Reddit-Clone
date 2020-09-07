from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/<uuid:pk>/', views.post_detail, name='post_detail'),
    path('sub/<uuid:pk>/', views.sub_detail, name='sub_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('post/<uuid:pk>/edit/', views.post_edit, name='post_edit'),
    path('post/<uuid:pk>/comment/', views.add_comment, name='add_comment_to_post'),
    path('post/<uuid:pk>/comment/<uuid:parent_pk>/', views.add_comment, name='add_reply_to_comment'),
    path('content/<uuid:pk>/upvote/', views.vote, {'is_upvote': True}, name='upvote'),
	path('content/<uuid:pk>/downvote/', views.vote, {'is_upvote': False}, name='downvote')
]