from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Account, Transaction, Category, SavingsGoal
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя пользователя',
            'type': 'text',
            'name': 'username'
        }),
        label='Имя пользователя'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль',
            'type': 'password',
            'name': 'password'
        }),
        label='Пароль'
    )

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя пользователя',
            'type': 'text',
            'name': 'username'
        }),
        label='Имя пользователя'
    )
    email = forms.EmailField(required=True, label='Email', widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль',
            'type': 'password',
            'name': 'password1'
        }),
        label='Пароль'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтвердите пароль',
            'type': 'password',
            'name': 'password2'
        }),
        label='Подтверждение пароля'
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'balance']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название аккаунта'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Начальный баланс', 'step': '0.01'}),
        }
        labels = {
            'name': 'Название аккаунта',
            'balance': 'Начальный баланс',
        }

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'description', 'date', 'transaction_type', 'category']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Сумма', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Описание'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'amount': 'Сумма',
            'description': 'Описание',
            'date': 'Дата',
            'transaction_type': 'Тип транзакции',
            'category': 'Категория',
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }
        labels = {
            'username': 'Имя пользователя',
            'email': 'Email',
        }

class CategoryQuickForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название категории'}),
        }
        labels = {
            'name': 'Название категории',
        }

class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ['title', 'target_amount', 'current_amount', 'deadline']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'На что копим?'}),
            'target_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Сумма цели'}),
            'current_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Уже накоплено'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'title': 'Цель',
            'target_amount': 'Сумма цели',
            'current_amount': 'Уже накоплено',
            'deadline': 'Дедлайн (необязательно)',
        } 