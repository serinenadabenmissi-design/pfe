# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from users.models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    
    # ⚠️ SUPPRIME 'username' de ordering
    ordering = ('email',)  # ← Trier par email au lieu de username
    
    list_display = ('email', 'first_name', 'last_name', 'get_role', 'is_staff', 'is_active')
    list_filter = ('profile__role', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )
    
    def get_role(self, obj):
        return obj.profile.role if hasattr(obj, 'profile') else 'client'
    get_role.short_description = 'Role'

admin.site.register(CustomUser, CustomUserAdmin)
