from django.urls import path
from . import views

urlpatterns = [
    path('posts/all/', views.get_all_posts, name='all-posts'),
    path('posts/pending/', views.get_pending_posts, name='pending-posts'),
    path('posts/create/', views.create_post, name='create-post'),
    path('posts/update/<int:post_id>/', views.update_post, name='update-post'),
    path('posts/delete/<int:post_id>/', views.delete_post, name='delete-post'),
    path('posts/approve/<int:post_id>/', views.approve_post, name='approve-post'),
    path('posts/<int:post_id>/', views.get_post_detail, name='post-detail'),
    path('my-posts/', views.get_my_posts, name='my-posts'),
    path('all-posts-admin/', views.get_all_posts_admin, name='all-posts-admin'),
    path('posts/<int:post_id>/admin/',  views.get_post_admin, name='post-admin'),
    path('posts/<int:post_id>/approve/',  views.approve_post, name='approve-post'),

]