# blog/admin.py

from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'title', 
        'category', 
        'author_name', 
        'status', 
        'created_at',
        'published_at'
    ]
    list_filter = [
        'status', 
        'category', 
        'created_at'
    ]
    search_fields = ['title', 'excerpt', 'author_name']
    readonly_fields = [
        'created_at', 
        'updated_at'
    ]
    list_editable = ['status']
    
    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'excerpt', 'content', 'category', 'featured_image')
        }),
        ('Publication', {
            'fields': ('status', 'author', 'author_name', 'read_time', 'key_points', 'featured')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        if obj.status == 'published' and not obj.published_at:
            from django.utils import timezone
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)