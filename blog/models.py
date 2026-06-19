# blog/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ('articles', 'Articles'),
        ('recipes', 'Healthy Recipes'),
        ('wellness', 'Wellness Tips'),
        ('nutrition', 'Nutrition'),
        ('success_stories', 'Success Stories'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]
    
    title = models.CharField(max_length=200)
    excerpt = models.CharField(max_length=300)
    content = models.TextField()
    featured_image = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='articles')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    read_time = models.CharField(max_length=50, default='5 min read')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts',
        null=True,
        blank=True
    )
    author_name = models.CharField(max_length=100, default='NutriLife Team')
    key_points = models.JSONField(default=list, blank=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_category_icon(self):
        icons = {
            'articles': '📰',
            'recipes': '🍳',
            'wellness': '🧘',
            'nutrition': '🍎',
            'success_stories': '⭐'
        }
        return icons.get(self.category, '📄')