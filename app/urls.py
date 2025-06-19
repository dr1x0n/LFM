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
    path('transactions/', views.transactions_list, name='transactions'),
    path('financial-tips/', views.financial_tips, name='financial_tips'),
    path('savings/', views.savings_list, name='savings_list'),
    path('savings/add/', views.savings_add, name='savings_add'),
    path('savings/edit/<int:goal_id>/', views.savings_edit, name='savings_edit'),
    path('savings/delete/<int:goal_id>/', views.savings_delete, name='savings_delete'),
    path('savings/deposit-ajax/<int:goal_id>/', views.savings_deposit_ajax, name='savings_deposit_ajax'),
    path('savings/withdraw-ajax/<int:goal_id>/', views.savings_withdraw_ajax, name='savings_withdraw_ajax'),
    path('delete-user/', views.delete_user, name='delete_user'),
    path('clear_transactions/', views.clear_transactions, name='clear_transactions'),
] 