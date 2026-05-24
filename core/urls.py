# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views  # ← IMPORTANT : importer les vues de core

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),
    
    # API Routes
    path('api/accounts/', include('accounts.urls')),
    path('api/users/', include('users.urls')),
    path('api/nutritionists/', include('nutritionists.urls')),
    path('api/consultations/', include('consultations.urls')),
    path('api/admin/', include('admin_dashboard.urls')),
    path('api/blog/', include('blog.urls')),
    path('payment/', include('payments.urls')),
    path('api/ai/', include('ai_tracker.urls')),
    # Frontend Pages
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
      path('blog/', views.blog, name='blog'), 
    path('feedback/', views.feedback_view, name='feedback'),
    path('contact/', views.contact_view, name='contact'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('admin-panel/', views.admin_dashboard_view, name='admin_dashboard'),
    path('nutritionist-dashboard/', views.nutritionist_dashboard_view, name='nutritionist_dashboard'),
    path('user-profile/', views.user_dashboard_view, name='user_dashboard'),
    path('select-nutri/', views.select_nutritionist_view, name='select_nutri'),
    path('trial-cons/', views.trial_consultation_view, name='trial_consultation'),
    path('payment/', views.payment_view, name='payment'),
    path('simple-consultation/', views.simple_cons, name='simple_consultation'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)