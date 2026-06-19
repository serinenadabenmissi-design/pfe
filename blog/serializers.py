# blog/serializers.py
from rest_framework import serializers
from .models import BlogPost

class BlogPostSerializer(serializers.ModelSerializer):
    author_email = serializers.SerializerMethodField()
    category_label = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = '__all__'
        read_only_fields = ['id', 'date_created', 'date_updated', 'author', 'status', 
                           'approved_by', 'approved_at', 'rejection_reason']
    
    def get_author_email(self, obj):
        return obj.author.email if obj.author else None
    
    def get_category_label(self, obj):
        return dict(BlogPost.CATEGORY_CHOICES).get(obj.category, obj.category)
    
    def get_status_display(self, obj):
        return dict(BlogPost.STATUS_CHOICES).get(obj.status, obj.status)
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_edit(request.user)
        return False
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_delete(request.user)
        return False

class CreateBlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = ['title', 'excerpt', 'content', 'category', 'image_url', 
                  'author_name_display', 'read_time', 'key_points', 
                  'recipe_emoji', 'recipe_tags', 'recipe_stats', 
                  'recipe_ingredients', 'recipe_steps']