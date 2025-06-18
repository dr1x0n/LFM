from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('add-account/', views.add_account, name='add_account'),
    path('switch-account/<str:username>/', views.switch_account, name='switch_account'),
    path('delete-saved-account/<str:username>/', views.delete_saved_account, name='delete_saved_account'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('edit-transaction/<int:transaction_id>/', views.edit_transaction, name='edit_transaction'),
    path('delete-transaction/<int:transaction_id>/', views.delete_transaction, name='delete_transaction'),
    path('delete-account/<int:account_id>/', views.delete_account, name='delete_account'),
    path('quick-actions/', views.quick_actions, name='quick_actions'),
    path('markets/', views.markets, name='markets'),
] 