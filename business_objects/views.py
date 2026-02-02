from rest_framework import viewsets, status
from rest_framework.response import Response
from permissions_system.permissions import HasResourcePermission, IsAuthenticated

# Имитация базы данных
MOCK_DOCUMENTS = [
    {"id": 1, "title": "Годовой отчет 2023", "content": "Секретные данные о прибыли..."},
    {"id": 2, "title": "Техническое задание", "content": "Описание архитектуры системы..."},
]

MOCK_PROJECTS = [
    {"id": 1, "name": "Проект Альфа", "status": "В разработке"},
    {"id": 2, "name": "Проект Бета", "status": "Завершен"},
]

class DocumentViewSet(viewsets.ViewSet):
    """
    Mock-ViewSet для документов.
    Требует разрешение 'document.read', 'document.create' и т.д.
    """
    permission_classes = [IsAuthenticated, HasResourcePermission]
    resource_type = 'document'

    def list(self, request):
        return Response(MOCK_DOCUMENTS)

    def retrieve(self, request, pk=None):
        doc = next((d for d in MOCK_DOCUMENTS if d["id"] == int(pk)), None)
        if doc:
            return Response(doc)
        return Response({"error": "Документ не найден"}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request):
        return Response({
            "message": "Документ успешно создан (MOCK)",
            "data": request.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        return Response({"message": f"Документ {pk} обновлен (MOCK)"})

    def destroy(self, request, pk=None):
        return Response({"message": f"Документ {pk} удален (MOCK)"}, status=status.HTTP_204_NO_CONTENT)


class ProjectViewSet(viewsets.ViewSet):
    """
    Mock-ViewSet для проектов.
    Требует разрешение 'project.read', 'project.create' и т.д.
    """
    permission_classes = [IsAuthenticated, HasResourcePermission]
    resource_type = 'project'

    def list(self, request):
        return Response(MOCK_PROJECTS)

    def retrieve(self, request, pk=None):
        proj = next((p for p in MOCK_PROJECTS if p["id"] == int(pk)), None)
        if proj:
            return Response(proj)
        return Response({"error": "Проект не найден"}, status=status.HTTP_404_NOT_FOUND)
