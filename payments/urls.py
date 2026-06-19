from django.urls import path
from django.shortcuts import render

def payment_page(request):
    return render(request, 'payment.html')

urlpatterns = [
    path('', payment_page, name='payment'),
]