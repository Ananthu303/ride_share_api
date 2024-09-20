from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import RegisterView, LoginView, DriverViewSet, RideViewSet,current_gps_location,RideRequestViewSet

router = DefaultRouter()
router.register(r'drivers', DriverViewSet)
router.register(r'rides', RideViewSet, basename='ride')
router.register(r'ride-requests', RideRequestViewSet, basename='ride-request')

urlpatterns = [
    path('',current_gps_location,name='current_gps_location'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls
