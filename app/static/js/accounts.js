document.addEventListener('DOMContentLoaded', function() {
    // Получаем CSRF токен
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    // Инициализация всех выпадающих меню
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const button = dropdown.querySelector('.account-actions-btn');
        const menu = dropdown.querySelector('.account-actions-menu');
        
        // Предотвращаем закрытие меню при клике внутри него
        menu.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        // Обработка клика по кнопке
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = menu.classList.contains('show');
            
            // Закрываем все другие открытые меню
            document.querySelectorAll('.account-actions-menu.show').forEach(openMenu => {
                if (openMenu !== menu) {
                    openMenu.classList.remove('show');
                }
            });

            // Переключаем текущее меню
            if (!isOpen) {
                menu.classList.add('show');
            }
        });
    });

    // Закрываем меню при клике вне его
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.account-actions-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });

    // Обработка переключения аккаунта
    document.querySelectorAll('.switch-account-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const username = this.dataset.username;
            
            // Создаем и отправляем форму для переключения аккаунта
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/switch-account/${username}/`;
            
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrfToken;
            
            form.appendChild(csrfInput);
            document.body.appendChild(form);
            form.submit();
        });
    });

    // Обработка удаления аккаунта
    document.querySelectorAll('.delete-account-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const username = this.dataset.username;
            if (confirm('Вы уверены, что хотите удалить этот аккаунт из сохраненных?')) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/delete-saved-account/${username}/`;
                
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = csrfToken;
                
                form.appendChild(csrfInput);
                document.body.appendChild(form);
                form.submit();
            }
        });
    });

    // Обработка показа/скрытия пароля
    window.togglePassword = function(inputId) {
        const input = document.getElementById(inputId);
        const type = input.type === 'password' ? 'text' : 'password';
        input.type = type;
        
        // Обновляем иконку
        const icon = input.nextElementSibling.querySelector('i');
        icon.classList.toggle('bi-eye');
        icon.classList.toggle('bi-eye-slash');
    };

    // Функция для показа уведомлений
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Автоматически скрываем уведомление через 5 секунд
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}); 