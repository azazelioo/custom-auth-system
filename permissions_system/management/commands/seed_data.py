from django.core.management.base import BaseCommand
from accounts.models import User
from permissions_system.models import Role, Permission, RolePermission, UserRole

class Command(BaseCommand):
    help = 'Заполняет базу данных начальными данными'

    def handle(self, *args, **options):
        self.stdout.write('Заполнение данных...')

        # 1. Создание разрешений
        permissions_data = [
            # Документы
            ('document.read', 'Чтение документов', 'document', 'read'),
            ('document.create', 'Создание документов', 'document', 'create'),
            ('document.update', 'Обновление документов', 'document', 'update'),
            ('document.delete', 'Удаление документов', 'document', 'delete'),
            # Проекты
            ('project.read', 'Чтение проектов', 'project', 'read'),
            ('project.create', 'Создание проектов', 'project', 'create'),
            ('project.update', 'Обновление проектов', 'project', 'update'),
            ('project.delete', 'Удаление проектов', 'project', 'delete'),
            # Администрирование
            ('admin.access', 'Доступ к панели управления', 'admin', 'access'),
        ]

        perms = {}
        for code, name, res_type, action in permissions_data:
            perm, _ = Permission.objects.get_or_create(
                code=code,
                defaults={'name': name, 'resource_type': res_type, 'action': action}
            )
            perms[code] = perm

        # 2. Создание ролей
        roles_data = {
            'admin': ['document.read', 'document.create', 'document.update', 'document.delete',
                      'project.read', 'project.create', 'project.update', 'project.delete',
                      'admin.access'],
            'manager': ['document.read', 'document.update', 'project.read', 'project.update'],
            'editor': ['document.create', 'document.update', 'project.create'],
            'viewer': ['document.read', 'project.read'],
        }

        for role_name, perm_codes in roles_data.items():
            role, _ = Role.objects.get_or_create(name=role_name)
            for code in perm_codes:
                RolePermission.objects.get_or_create(role=role, permission=perms[code])

        # 3. Создание тестовых пользователей
        users_data = [
            ('admin@test.com', 'admin123', 'admin', 'Иван', 'Админов'),
            ('manager@test.com', 'manager123', 'manager', 'Петр', 'Менеджеров'),
            ('editor@test.com', 'editor123', 'editor', 'Алексей', 'Редакторов'),
            ('viewer@test.com', 'viewer123', 'viewer', 'Мария', 'Зритель'),
        ]

        for email, password, role_name, first_name, last_name in users_data:
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=(role_name == 'admin'),
                )
                role = Role.objects.get(name=role_name)
                UserRole.objects.create(user=user, role=role)
                self.stdout.write(f'Создан пользователь: {email} ({role_name})')

        self.stdout.write(self.style.SUCCESS('Данные успешно загружены!'))
