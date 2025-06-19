from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from .models import Transaction, Category, Account, SavedAccount, SavingsGoal
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from .forms import AccountForm, TransactionForm, CustomUserCreationForm, CategoryQuickForm, SavingsGoalForm
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect
from django.db import connection
from django import forms
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

def register(request):
    if request.user.is_authenticated:
        logout(request)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
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
    # Общий баланс = доходы - расходы (накопления уже учтены в транзакциях)
    total_balance = total_income - total_expenses
    context = get_base_context(request)
    context.update({
        'title': 'Главная',
        'transactions': Transaction.objects.filter(user=request.user).order_by('-date', '-id')[:5],
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_balance': total_balance,
        'transactions_count': Transaction.objects.filter(user=request.user).count(),
    })
    return render(request, 'dashboard.html', context)

@login_required
def profile(request):
    try:
        user = request.user
        days_registered = (timezone.now().date() - user.date_joined.date()).days
        transactions_count = Transaction.objects.filter(user=user).count()
        accounts_count = Account.objects.filter(user=user, is_active=True).count()
        recent_transactions = Transaction.objects.filter(user=user).order_by('-date', '-id')[:10]
        total_income = Transaction.objects.filter(user=user, transaction_type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_expenses = Transaction.objects.filter(user=user, transaction_type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_balance = total_income - total_expenses

        # Агрегация расходов по категориям
        expense_transactions = Transaction.objects.filter(user=user, transaction_type='expense', category__isnull=False)
        category_sums = expense_transactions.values('category__name').annotate(amount=Sum('amount')).order_by('-amount')
        # Цвета для категорий (можно расширить)
        category_colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#00C49A', '#FF6F91', '#FFD700', '#8B5CF6', '#00BFFF', '#FF8C00'
        ]
        spending_by_category = []
        for idx, item in enumerate(category_sums):
            spending_by_category.append({
                'category': item['category__name'],
                'amount': float(item['amount']),
                'color': category_colors[idx % len(category_colors)]
            })
        total_spending = sum(item['amount'] for item in spending_by_category)
        for item in spending_by_category:
            item['percentage'] = round((item['amount'] / total_spending) * 100, 1) if total_spending else 0

        saved_account = SavedAccount.objects.filter(main_user=user, username=user.username).order_by('-last_used').first()
        user_password = saved_account.password if saved_account else None

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
            'user_password': user_password,
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
            'user_password': None,
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
        account.delete()
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
    # Автоматически создаём стандартные категории, если их нет
    if not Category.objects.filter(user=request.user).exists():
        default_cats = [
            'Продукты', 'Транспорт', 'Развлечения', 'Здоровье', 'Образование',
            'Одежда', 'Коммунальные услуги', 'Зарплата', 'Подработка', 'Инвестиции', 'Другое'
        ]
        for name in default_cats:
            Category.objects.create(user=request.user, name=name)
    category_form = None
    category_created = False
    if request.method == 'POST' and 'add_category' in request.POST:
        category_form = CategoryQuickForm(request.POST)
        if category_form.is_valid():
            new_cat = category_form.save(commit=False)
            new_cat.user = request.user
            new_cat.save()
            category_created = True
            messages.success(request, f'Категория "{new_cat.name}" добавлена!')
        form = TransactionForm()
        form.fields['category'].queryset = Category.objects.filter(user=request.user)
    elif request.method == 'POST':
        form = TransactionForm(request.POST)
        form.fields['category'].queryset = Category.objects.filter(user=request.user)
        if form.is_valid():
            try:
                transaction = form.save(commit=False)
                transaction.user = request.user
                transaction.save()
                messages.success(request, 'Транзакция успешно добавлена')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении транзакции: {str(e)}')
        else:
            messages.error(request, 'Пожалуйста, проверьте правильность введенных данных')
    else:
        form = TransactionForm()
        form.fields['category'].queryset = Category.objects.filter(user=request.user)
        category_form = CategoryQuickForm()
    context = get_base_context(request)
    context.update({
        'title': 'Добавить транзакцию',
        'form': form,
        'category_form': category_form or CategoryQuickForm(),
        'category_created': category_created,
    })
    return render(request, 'add_transaction.html', context)

@csrf_protect
def add_account(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        # save_account = request.POST.get('save_account') == 'on'  # больше не нужен

        if not username or not password:
            messages.error(request, 'Имя пользователя и пароль обязательны')
            return render(request, 'add_account.html')

        try:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Если пользователь залогинен — создаём дополнительный аккаунт
                if request.user.is_authenticated:
                    try:
                        SavedAccount.objects.filter(
                            username=username,
                            main_user=request.user
                        ).delete()
                        SavedAccount.objects.create(
                            username=username,
                            password=password,
                            main_user=request.user,
                            last_used=timezone.now()
                        )
                    except Exception as e:
                        messages.error(request, 'Ошибка при сохранении аккаунта')
                        return render(request, 'add_account.html')
                    login(request, user)
                    messages.success(request, f'Успешный вход в аккаунт {username}')
                    return redirect('dashboard')
                else:
                    # Если не залогинен — логиним и создаём SavedAccount для себя
                    login(request, user)
                    SavedAccount.objects.create(
                        username=username,
                        password=password,
                        main_user=user,
                        last_used=timezone.now()
                    )
                    messages.success(request, f'Аккаунт создан и выполнен вход: {username}')
                    return redirect('dashboard')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
                return render(request, 'add_account.html')
        except Exception as e:
            messages.error(request, f'Ошибка при входе: {str(e)}')
            return render(request, 'add_account.html')

    # GET-запрос или после ошибки
    return render(request, 'add_account.html')

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

@login_required
def transactions_list(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    context = get_base_context(request)
    context.update({
        'transactions': transactions,
        'title': 'Все транзакции',
    })
    return render(request, 'transactions_list.html', context)

@login_required
def financial_tips(request):
    tips = [
        {
            'icon': 'fas fa-piggy-bank',
            'title': 'Создайте резервный фонд',
            'text': 'Откладывайте 10-20% от дохода на непредвиденные расходы. Это поможет избежать долгов в сложные времена.',
            'url': 'https://xn--h1alcedd.xn--d1aqf.xn--p1ai/instructions/finansovaya-gramotnost-chto-eto-takoe-i-kak-ee-povysit/'
        },
        {
            'icon': 'fas fa-chart-pie',
            'title': 'Ведите бюджет',
            'text': 'Регулярно отслеживайте доходы и расходы. Это поможет понять, куда уходят деньги и где можно сэкономить.',
            'url': 'https://journal.tinkoff.ru/financial-rules-investing-small-change-in-iia/'
        },
        {
            'icon': 'fas fa-credit-card',
            'title': 'Избегайте импульсных покупок',
            'text': 'Перед крупной покупкой подумайте, действительно ли она вам нужна. Это поможет избежать лишних трат.',
            'url': 'https://journal.tinkoff.ru/news/finzachet-2024/'
        },
        {
            'icon': 'fas fa-user-graduate',
            'title': 'Инвестируйте в себя',
            'text': 'Образование и новые навыки — лучшая инвестиция, которая окупится в будущем.',
            'url': 'https://journal.tinkoff.ru/financial-rules-investing-small-change-in-iia/'
        },
        {
            'icon': 'fas fa-coins',
            'title': 'Планируйте крупные покупки',
            'text': 'Ставьте финансовые цели и планируйте бюджет, чтобы накопить на важные вещи.',
            'url': 'https://xn--h1alcedd.xn--d1aqf.xn--p1ai/instructions/finansovaya-gramotnost-chto-eto-takoe-i-kak-ee-povysit/'
        },
        {
            'icon': 'fas fa-shield-alt',
            'title': 'Защищайте свои финансы',
            'text': 'Будьте осторожны с мошенниками, не сообщайте свои данные третьим лицам.',
            'url': 'https://xn--h1alcedd.xn--d1aqf.xn--p1ai/instructions/finansovaya-gramotnost-chto-eto-takoe-i-kak-ee-povysit/'
        },
        {
            'icon': 'fas fa-balance-scale',
            'title': 'Сравнивайте цены и условия',
            'text': 'Перед покупкой или оформлением услуги сравните предложения разных компаний.',
            'url': 'https://journal.tinkoff.ru/compare/'
        },
        {
            'icon': 'fas fa-calendar-check',
            'title': 'Платите счета вовремя',
            'text': 'Это поможет избежать штрафов и сохранить хорошую кредитную историю.',
            'url': 'https://journal.tinkoff.ru/guide/credit-history/'
        },
        {
            'icon': 'fas fa-hand-holding-usd',
            'title': 'Контролируйте кредиты',
            'text': 'Старайтесь не брать кредиты на потребление и всегда рассчитывайте свою долговую нагрузку.',
            'url': 'https://journal.tinkoff.ru/guide/credit/'
        },
        {
            'icon': 'fas fa-lightbulb',
            'title': 'Ставьте финансовые цели',
            'text': 'Определите конкретные цели и сроки их достижения. Это мотивирует и помогает планировать.',
            'url': 'https://journal.tinkoff.ru/goal/'
        },
        {
            'icon': 'fas fa-book',
            'title': 'Читайте о финансах',
            'text': 'Постоянно повышайте свою финансовую грамотность — это инвестиция в ваше будущее.',
            'url': 'https://journal.tinkoff.ru/list/finliteracy/'
        },
        {
            'icon': 'fas fa-gift',
            'title': 'Используйте бонусы и кэшбэк',
            'text': 'Пользуйтесь программами лояльности, чтобы экономить на покупках.',
            'url': 'https://journal.tinkoff.ru/guide/cashback/'
        },
        {
            'icon': 'fas fa-seedling',
            'title': 'Экологичное потребление',
            'text': 'Покупайте только то, что действительно нужно. Это экономит деньги и бережёт природу.',
            'url': 'https://journal.tinkoff.ru/guide/eco/'
        },
        {
            'icon': 'fas fa-heartbeat',
            'title': 'Заботьтесь о здоровье',
            'text': 'Профилактика заболеваний дешевле лечения. Вкладывайтесь в здоровье и спорт.',
            'url': 'https://journal.tinkoff.ru/guide/health/'
        },
        {
            'icon': 'fas fa-users',
            'title': 'Обсуждайте финансы с близкими',
            'text': 'Открытое обсуждение бюджета помогает избегать конфликтов и достигать целей вместе.',
            'url': 'https://journal.tinkoff.ru/guide/family-budget/'
        },
        {
            'icon': 'fas fa-bullseye',
            'title': 'Делайте регулярные сбережения',
            'text': 'Откладывайте небольшие суммы регулярно, чтобы накопить на крупные цели.',
            'url': 'https://journal.tinkoff.ru/guide/savings/'
        },
        {
            'icon': 'fas fa-university',
            'title': 'Изучайте банковские продукты',
            'text': 'Разбирайтесь в условиях вкладов, кредитов и карт, чтобы выбирать лучшие предложения.',
            'url': 'https://journal.tinkoff.ru/guide/bank-products/'
        },
        {
            'icon': 'fas fa-chart-line',
            'title': 'Инвестируйте с умом',
            'text': 'Изучайте основы инвестирования и не вкладывайте все деньги в один актив.',
            'url': 'https://journal.tinkoff.ru/guide/invest/'
        },
        {
            'icon': 'fas fa-exclamation-triangle',
            'title': 'Остерегайтесь мошенников',
            'text': 'Проверяйте информацию и не переходите по подозрительным ссылкам.',
            'url': 'https://journal.tinkoff.ru/guide/scam/'
        },
        {
            'icon': 'fas fa-mobile-alt',
            'title': 'Используйте финансовые приложения',
            'text': 'Приложения помогают контролировать расходы и планировать бюджет.',
            'url': 'https://journal.tinkoff.ru/guide/apps/'
        },
        {
            'icon': 'fas fa-globe-europe',
            'title': 'Планируйте путешествия заранее',
            'text': 'Раннее бронирование и сравнение цен помогает экономить на поездках.',
            'url': 'https://journal.tinkoff.ru/guide/travel/'
        },
    ]
    context = get_base_context(request)
    context['tips'] = tips
    context['title'] = 'Финансовые подсказки'
    return render(request, 'financial_tips.html', context)

@login_required
def savings_list(request):
    goals = SavingsGoal.objects.filter(user=request.user).order_by('-created_at')
    # Берём первый активный аккаунт пользователя
    account = Account.objects.filter(user=request.user, is_active=True).first()
    context = get_base_context(request)
    context.update({'goals': goals, 'title': 'Мои накопления', 'account': account})
    return render(request, 'savings_list.html', context)

@login_required
def savings_add(request):
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, 'Цель успешно добавлена!')
            return redirect('savings_list')
    else:
        form = SavingsGoalForm()
    context = get_base_context(request)
    context.update({'form': form, 'title': 'Новая цель накоплений'})
    return render(request, 'savings_add.html', context)

@login_required
def savings_edit(request, goal_id):
    goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Цель обновлена!')
            return redirect('savings_list')
    else:
        form = SavingsGoalForm(instance=goal)
    context = get_base_context(request)
    context.update({'form': form, 'goal': goal, 'title': 'Редактировать цель'})
    return render(request, 'savings_edit.html', context)

@login_required
def savings_delete(request, goal_id):
    goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, 'Цель удалена!')
        return redirect('savings_list')
    context = get_base_context(request)
    context.update({'goal': goal, 'title': 'Удалить цель'})
    return render(request, 'savings_delete.html', context)

class SavingsGoalTransactionForm(forms.Form):
    amount = forms.DecimalField(min_value=0.01, max_digits=12, decimal_places=2, label='Сумма', widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Сумма'}))

@require_POST
@login_required
def savings_deposit_ajax(request, goal_id):
    import json
    from django.utils import timezone
    try:
        data = json.loads(request.body)
        amount = Decimal(data.get('amount', '0'))
        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'Введите корректную сумму!'}, status=400)
        goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
        # Получаем или создаём категорию для пополнения накопления
        category, _ = Category.objects.get_or_create(user=request.user, name='Пополнение накопления')
        with transaction.atomic():
            # Создаём транзакцию (расход)
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                description=f'Пополнение цели "{goal.title}"',
                date=timezone.now().date(),
                transaction_type='expense',
                category=category
            )
            # Пополняем накопление
            goal.current_amount += amount
            goal.save()
        return JsonResponse({'success': True, 'new_balance': None, 'new_goal': str(goal.current_amount)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
@login_required
def savings_withdraw_ajax(request, goal_id):
    import json
    from django.utils import timezone
    try:
        data = json.loads(request.body)
        amount = Decimal(data.get('amount', '0'))
        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'Введите корректную сумму!'}, status=400)
        goal = get_object_or_404(SavingsGoal, id=goal_id, user=request.user)
        if goal.current_amount < amount:
            return JsonResponse({'success': False, 'error': 'Недостаточно средств на цели!'}, status=400)
        # Получаем или создаём категорию для вывода с накопления
        category, _ = Category.objects.get_or_create(user=request.user, name='Вывод с накопления')
        with transaction.atomic():
            # Создаём транзакцию (доход)
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                description=f'Вывод с цели "{goal.title}"',
                date=timezone.now().date(),
                transaction_type='income',
                category=category
            )
            # Снимаем с накопления
            goal.current_amount -= amount
            goal.save()
        return JsonResponse({'success': True, 'new_balance': None, 'new_goal': str(goal.current_amount)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def delete_user(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Ваш аккаунт был полностью удалён.')
        return redirect('dashboard')
    return render(request, 'delete_user_confirm.html')

@login_required
def clear_transactions(request):
    if request.method == 'POST':
        Transaction.objects.filter(user=request.user).delete()
        messages.success(request, 'Вся история транзакций успешно очищена!')
    return redirect('profile')
