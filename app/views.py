from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from .models import Transaction, Category, Account, SavedAccount
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from .forms import AccountForm, TransactionForm
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect
from django.db import connection

def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('login')

@login_required
def dashboard(request):
    """Представление для главной страницы"""
    total_income = Transaction.objects.filter(user=request.user, transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = Transaction.objects.filter(user=request.user, transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0
    total_balance = total_income - total_expenses
    
    context = get_base_context(request)
    context.update({
        'title': 'Главная',
        'transactions': Transaction.objects.filter(user=request.user).order_by('-date')[:5],
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_balance': total_balance,
    })
    return render(request, 'dashboard.html', context)

@login_required
def profile(request):
    try:
        # Получаем данные пользователя
        user = request.user
        days_registered = (timezone.now().date() - user.date_joined.date()).days
        transactions_count = Transaction.objects.filter(user=user).count()
        accounts_count = Account.objects.filter(user=user, is_active=True).count()
        
        # Получаем последние транзакции
        recent_transactions = Transaction.objects.filter(user=user).order_by('-date')[:10]
        
        # Рассчитываем общие суммы
        total_income = Transaction.objects.filter(user=user, transaction_type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_expenses = Transaction.objects.filter(user=user, transaction_type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_balance = total_income - total_expenses
        
        # Статистика трат по категориям
        spending_by_category = [
            {"category": "Продукты", "amount": 12500, "color": "#FF6384"},
            {"category": "Транспорт", "amount": 8500, "color": "#36A2EB"},
            {"category": "Развлечения", "amount": 6200, "color": "#FFCE56"},
            {"category": "Коммунальные услуги", "amount": 4800, "color": "#4BC0C0"},
            {"category": "Одежда", "amount": 3200, "color": "#9966FF"},
            {"category": "Здоровье", "amount": 2800, "color": "#FF9F40"},
        ]
        
        # Общая сумма трат
        total_spending = sum(item["amount"] for item in spending_by_category)
        
        # Добавляем процент для каждой категории
        for item in spending_by_category:
            item["percentage"] = round((item["amount"] / total_spending) * 100, 1)
        
        context = get_base_context(request)
        context.update({
            'days_registered': days_registered,
            'transactions_count': transactions_count,
            'accounts_count': accounts_count,
            'recent_transactions': recent_transactions,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'total_balance': total_balance,
            'spending_by_category': spending_by_category,
            'total_spending': total_spending,
        })
        
        return render(request, 'profile.html', context)
        
    except Exception as e:
        messages.error(request, f'Ошибка при загрузке данных: {str(e)}')
        context = get_base_context(request)
        context.update({
            'days_registered': 0,
            'transactions_count': 0,
            'accounts_count': 0,
            'recent_transactions': [],
            'total_income': Decimal('0'),
            'total_expenses': Decimal('0'),
            'total_balance': Decimal('0'),
            'spending_by_category': [],
            'total_spending': 0,
        })
        return render(request, 'profile.html', context)

@login_required
def create_account(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        initial_balance = Decimal(request.POST.get('initial_balance', '0.00'))
        
        if not name:
            messages.error(request, 'Название аккаунта обязательно')
            return redirect('profile')
        
        account = Account.objects.create(
            user=request.user,
            name=name,
            balance=initial_balance
        )
        
        request.session['active_account'] = account.id
        messages.success(request, f'Аккаунт "{name}" успешно создан')
        return redirect('profile')
    
    return render(request, 'create_account.html')

@login_required
def switch_account(request, username):
    try:
        # Получаем самую последнюю запись для этого username
        saved_account = SavedAccount.objects.filter(
            username=username
        ).order_by('-last_used').first()
        
        if not saved_account:
            messages.error(request, 'Аккаунт не найден')
            return redirect('dashboard')
            
        user = authenticate(request, username=username, password=saved_account.password)
        if user is not None:
            # Обновляем last_used перед входом
            saved_account.save()
            # Выполняем вход в аккаунт
            login(request, user)
            messages.success(request, f'Успешное переключение на аккаунт {username}')
        else:
            messages.error(request, 'Ошибка при переключении аккаунта')
    except Exception as e:
        messages.error(request, f'Ошибка при переключении: {str(e)}')
    return redirect('dashboard')

@login_required
def delete_account(request, account_id):
    account = get_object_or_404(Account, id=account_id, user=request.user)
    
    if request.method == 'POST':
        account.is_active = False
        account.save()
        
        # Если удаляемый аккаунт был активным, переключаемся на другой
        if request.session.get('active_account') == account.id:
            other_account = Account.objects.filter(user=request.user, is_active=True).first()
            if other_account:
                request.session['active_account'] = other_account.id
            else:
                request.session.pop('active_account', None)
        
        messages.success(request, f'Аккаунт "{account.name}" удален')
        return redirect('profile')
    
    return render(request, 'delete_account.html', {'account': account})

@login_required
def add_transaction(request):
    """Представление для добавления транзакции"""
    print("=== Starting add_transaction view ===")
    print(f"Request method: {request.method}")
    print(f"User: {request.user.username}")
    
    if request.method == 'POST':
        print("Processing POST request")
        form = TransactionForm(request.POST)
        print(f"Form data: {request.POST}")
        
        if form.is_valid():
            print("Form is valid")
            try:
                transaction = form.save(commit=False)
                transaction.user = request.user
                transaction.save()
                print(f"Transaction saved: {transaction}")
                messages.success(request, 'Транзакция успешно добавлена')
                return redirect('dashboard')
            except Exception as e:
                print(f"Error saving transaction: {str(e)}")
                messages.error(request, f'Ошибка при сохранении транзакции: {str(e)}')
        else:
            print(f"Form errors: {form.errors}")
            messages.error(request, 'Пожалуйста, проверьте правильность введенных данных')
    else:
        form = TransactionForm()
    
    context = get_base_context(request)
    context.update({
        'title': 'Добавить транзакцию',
        'form': form,
    })
    return render(request, 'add_transaction.html', context)

@login_required
@csrf_protect
def add_account(request):
    print("=== Starting add_account view ===")
    print(f"Request method: {request.method}")
    print(f"User: {request.user.username}")
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        save_account = request.POST.get('save_account') == 'on'
        
        print(f"Form data:")
        print(f"- Username: {username}")
        print(f"- Save account: {save_account}")
        print(f"- CSRF Token: {request.POST.get('csrfmiddlewaretoken')}")

        if not username or not password:
            print("Error: Username or password is empty")
            messages.error(request, 'Имя пользователя и пароль обязательны')
            return redirect('dashboard')

        try:
            # Сначала проверяем аутентификацию
            user = authenticate(request, username=username, password=password)
            print(f"Authentication result: {user is not None}")
            
            if user is not None:
                # Сохраняем аккаунт перед входом
                if save_account:
                    print("Attempting to save account...")
                    try:
                        # Удаляем все существующие записи для этого username
                        SavedAccount.objects.filter(
                            username=username,
                            main_user=request.user
                        ).delete()
                        
                        # Создаем новую запись
                        saved = SavedAccount.objects.create(
                            username=username,
                            password=password,
                            main_user=request.user,
                            last_used=timezone.now()
                        )
                        print(f"Created new account: {saved}")
                            
                        # Проверяем, что аккаунт действительно сохранился
                        saved_accounts = SavedAccount.objects.filter(main_user=request.user)
                        print(f"Total saved accounts for user: {saved_accounts.count()}")
                        for acc in saved_accounts:
                            print(f"- {acc.username} (last used: {acc.last_used})")
                            
                    except Exception as e:
                        print(f"Error saving account: {str(e)}")
                        messages.error(request, 'Ошибка при сохранении аккаунта')
                        return redirect('dashboard')
                
                # Выполняем вход в аккаунт
                print("Logging in...")
                login(request, user)
                print("Login successful")
                messages.success(request, f'Успешный вход в аккаунт {username}')
                return redirect('dashboard')
            else:
                print("Authentication failed")
                messages.error(request, 'Неверное имя пользователя или пароль')
        except Exception as e:
            print(f"Error during login: {str(e)}")
            messages.error(request, f'Ошибка при входе: {str(e)}')
    
    print("=== Ending add_account view ===")
    # Если это GET запрос или произошла ошибка, показываем форму
    context = get_base_context(request)
    return render(request, 'dashboard.html', context)

def get_base_context(request):
    # Получаем все сохраненные аккаунты для текущего пользователя
    saved_accounts = SavedAccount.objects.filter(
        main_user=request.user
    ).order_by('-last_used')
    
    print(f"Found {saved_accounts.count()} saved accounts for user {request.user.username}")
    for acc in saved_accounts:
        print(f"- {acc.username} (last used: {acc.last_used})")
    
    context = {
        'saved_accounts': saved_accounts
    }
    return context

def edit_transaction(request, transaction_id):
    """Представление для редактирования транзакции"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = TransactionForm(instance=transaction)
    
    context = get_base_context(request)
    context.update({
        'title': 'Редактировать транзакцию',
        'form': form,
    })
    return render(request, 'edit_transaction.html', context)

def delete_transaction(request, transaction_id):
    """Представление для удаления транзакции"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    transaction.delete()
    return redirect('dashboard')

@login_required
def delete_saved_account(request, username):
    try:
        # Удаляем все записи для этого username
        SavedAccount.objects.filter(username=username).delete()
        messages.success(request, f'Аккаунт {username} удален из сохраненных')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении: {str(e)}')
    return redirect('dashboard')

@login_required
def quick_actions(request):
    context = get_base_context(request)
    return render(request, 'quick_actions.html', context)

@login_required
def markets(request):
    # Расширенные данные валют и акций
    currencies = [
        {"name": "USD/RUB", "value": 92.5, "change": 0.7, "history": [91.8, 92.0, 92.3, 92.5]},
        {"name": "EUR/RUB", "value": 100.2, "change": -0.3, "history": [100.8, 100.5, 100.3, 100.2]},
        {"name": "CNY/RUB", "value": 12.8, "change": 0.2, "history": [12.6, 12.7, 12.7, 12.8]},
        {"name": "GBP/RUB", "value": 118.4, "change": -0.8, "history": [119.2, 118.9, 118.6, 118.4]},
        {"name": "JPY/RUB", "value": 0.62, "change": 0.01, "history": [0.61, 0.61, 0.62, 0.62]},
        {"name": "CHF/RUB", "value": 103.7, "change": 0.5, "history": [103.2, 103.4, 103.6, 103.7]},
    ]
    stocks = [
        {"name": "SBER", "value": 270.1, "change": 1.2, "history": [268.0, 269.0, 269.5, 270.1]},
        {"name": "GAZP", "value": 170.8, "change": -0.6, "history": [171.5, 171.0, 170.9, 170.8]},
        {"name": "LKOH", "value": 7450.0, "change": 2.1, "history": [7300.0, 7350.0, 7400.0, 7450.0]},
        {"name": "YNDX", "value": 2850.0, "change": -1.5, "history": [2890.0, 2870.0, 2860.0, 2850.0]},
        {"name": "VKUS", "value": 125.0, "change": 3.2, "history": [121.0, 122.5, 123.8, 125.0]},
        {"name": "TATN", "value": 580.0, "change": 0.8, "history": [575.0, 577.0, 578.5, 580.0]},
        {"name": "NVTK", "value": 1850.0, "change": -0.9, "history": [1867.0, 1860.0, 1855.0, 1850.0]},
        {"name": "ROSN", "value": 620.0, "change": 1.7, "history": [610.0, 615.0, 618.0, 620.0]},
    ]
    context = get_base_context(request)
    context.update({"currencies": currencies, "stocks": stocks})
    return render(request, 'markets.html', context)
