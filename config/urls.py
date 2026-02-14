from django.urls import path, include

urlpatterns = [
    path('', include('credit_app.urls')),
]
