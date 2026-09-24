from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("token/", views.CustomTokenObtainPairView.as_view(), name="auth-token"),
    path("token/refresh/", views.CookieTokenRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("google/", views.GoogleAuthView.as_view(), name="auth-google"),
    path("me/", views.MeView.as_view(), name="auth-me"),
]
