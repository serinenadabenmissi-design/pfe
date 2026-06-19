# blog/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from .models import BlogPost
from nutritionists.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_posts(request):
    """Récupère tous les posts publiés pour le frontend"""
    category = request.GET.get('category', 'all')
    
    posts = BlogPost.objects.filter(status='published')
    
    if category != 'all':
        posts = posts.filter(category=category)
    
    posts = posts.order_by('-featured', '-created_at')
    
    return Response([
        {
            'id': p.id,
            'title': p.title,
            'excerpt': p.excerpt,
            'content': p.content,
            'featured_image': p.featured_image,
            'category': p.category,
            'read_time': p.read_time,
            'author_name': p.author_name,
            'created_at': p.created_at.isoformat(),
            'key_points': p.key_points,
            'featured': p.featured,
            'icon': p.get_category_icon(),
        }
        for p in posts
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_posts(request):
    """Récupère les posts en attente d'approbation (pour admin)"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # Récupérer les posts avec status='pending'
    posts = BlogPost.objects.filter(status='pending').order_by('-created_at')
    
    print(f"🔍 Pending posts found: {posts.count()}")  # Debug
    
    return Response([
        {
            'id': p.id,
            'title': p.title,
            'excerpt': p.excerpt,
            'content': p.content,
            'featured_image': p.featured_image,
            'category': p.category,
            'read_time': p.read_time,
            'author_name': p.author_name,
            'created_at': p.created_at.isoformat(),
            'key_points': p.key_points,
            'author_id': p.author.id if p.author else None,
        }
        for p in posts
    ])

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_post(request):
    """Créer un nouvel article"""
    data = request.data
    
    post = BlogPost.objects.create(
        title=data['title'],
        excerpt=data.get('excerpt', ''),
        content=data.get('content', ''),
        featured_image=data.get('featured_image', ''),
        category=data.get('category', 'articles'),
        read_time=data.get('read_time', '5 min read'),
        author=request.user,
        author_name=data.get('author_name', request.user.get_full_name() or 'NutriLife Team'),
        key_points=data.get('key_points', []),
        status='pending',  # ← Important : en attente d'approbation
    )
    
    print(f"📝 New post created: {post.title} (status: {post.status})")  # Debug
    
    # Notifier l'admin
    admins = User.objects.filter(is_superuser=True)
    for admin in admins:
        Notification.objects.create(
            user=admin,  # ← Utilise user=admin au lieu de nutritionist=None
            is_admin_notification=True,
            notification_type='blog_pending',
            title='📝 New Blog Post Pending',
            message=f'{request.user.get_full_name()} has submitted a new article: "{post.title}"',
            related_id=post.id,
            is_read=False
        )
    
    return Response({
        'success': True,
        'message': 'Article submitted for review',
        'post_id': post.id
    }, status=201)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_post(request, post_id):
    """Mettre à jour un article"""
    try:
        post = BlogPost.objects.get(id=post_id)
    except BlogPost.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    
    data = request.data
    
    post.title = data.get('title', post.title)
    post.excerpt = data.get('excerpt', post.excerpt)
    post.content = data.get('content', post.content)
    post.featured_image = data.get('featured_image', post.featured_image)
    post.category = data.get('category', post.category)
    post.read_time = data.get('read_time', post.read_time)
    post.author_name = data.get('author_name', post.author_name)
    post.key_points = data.get('key_points', post.key_points)
    
    if data.get('status'):
        post.status = data['status']
    
    post.save()
    
    return Response({'success': True, 'message': 'Article updated'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    """Supprimer un article"""
    try:
        post = BlogPost.objects.get(id=post_id)
        post.delete()
        return Response({'success': True, 'message': 'Article deleted'})
    except BlogPost.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_post(request, post_id):
    """Approuver ou rejeter un article (admin seulement)"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        post = BlogPost.objects.get(id=post_id)
    except BlogPost.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    
    action = request.data.get('action')
    explanation = request.data.get('explanation', '')
    
    if action == 'approve':
        post.status = 'published'
        post.published_at = timezone.now()
        message = f'✅ Your article "{post.title}" has been published!'
        title = 'Article Published'
    elif action == 'reject':
        post.status = 'rejected'
        message = f'❌ Your article "{post.title}" was rejected. Reason: {explanation}'
        title = 'Article Update'
    else:
        return Response({'error': 'Invalid action'}, status=400)
    
    post.save()
    
    # Notifier l'auteur
    if post.author:
        Notification.objects.create(
            user=post.author,
            notification_type='blog_update',
            title=title,
            message=message,
            related_id=post.id,
            is_read=False
        )
    
    return Response({'success': True, 'message': f'Article {action}d'})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_post_detail(request, post_id):
    """Récupérer un article spécifique"""
    try:
        post = BlogPost.objects.get(id=post_id, status='published')
    except BlogPost.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    
    return Response({
        'id': post.id,
        'title': post.title,
        'excerpt': post.excerpt,
        'content': post.content,
        'featured_image': post.featured_image,
        'category': post.category,
        'read_time': post.read_time,
        'author_name': post.author_name,
        'created_at': post.created_at.isoformat(),
        'key_points': post.key_points,
        'icon': post.get_category_icon(),
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_posts(request):
    """Récupère les articles de l'utilisateur connecté (nutritionniste)"""
    posts = BlogPost.objects.filter(author=request.user).order_by('-created_at')
    return Response([{
        'id': p.id,
        'title': p.title,
        'category': p.category,
        'status': p.status,
        'created_at': p.created_at.isoformat(),
    } for p in posts])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_posts_admin(request):
    """Récupère tous les articles pour l'admin"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    # Récupérer TOUS les posts (pas de filtre sur le statut)
    posts = BlogPost.objects.all().order_by('-created_at')
    
    print(f"🔍 All posts for admin: {posts.count()}")  # Debug
    
    return Response([{
        'id': p.id,
        'title': p.title,
        'author_name': p.author_name,
        'category': p.category,
        'status': p.status,  # Important : inclure le statut
        'created_at': p.created_at.isoformat(),
        'excerpt': p.excerpt,
        'content': p.content,
        'featured_image': p.featured_image,
        'read_time': p.read_time,
        'key_points': p.key_points,
    } for p in posts])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_post_admin(request, post_id):
    """Récupère un article spécifique pour l'admin"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=403)
    
    try:
        post = BlogPost.objects.get(id=post_id)
        return Response({
            'id': post.id,
            'title': post.title,
            'excerpt': post.excerpt,
            'content': post.content,
            'featured_image': post.featured_image,
            'category': post.category,
            'status': post.status,
            'read_time': post.read_time,
            'author_name': post.author_name,
            'created_at': post.created_at.isoformat(),
            'key_points': post.key_points,
        })
    except BlogPost.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)