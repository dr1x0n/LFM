from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Account, Transaction
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
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите email',
            'type': 'email',
            'name': 'email'
        }),
        label='Email'
    )
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
        model = UserCreationForm.Meta.model
        fields = ('username', 'email', 'password1', 'password2')

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
        fields = ['amount', 'description', 'date', 'transaction_type']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Сумма', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Описание'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'amount': 'Сумма',
            'description': 'Описание',
            'date': 'Дата',
            'transaction_type': 'Тип транзакции',
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