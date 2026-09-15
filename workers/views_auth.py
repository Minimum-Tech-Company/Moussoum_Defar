from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Worker
from .serializers import (
    WorkerRegisterSerializer, WorkerLoginSerializer,
    WorkerSerializer, WorkerUpdateSerializer
)


class WorkerRegisterView(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = WorkerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        worker = serializer.save()

        refresh = RefreshToken.for_user(worker.user)

        return Response({
            'user': {
                'id': worker.user.id,
                'username': worker.user.username,
                'email': worker.user.email,
            },
            'worker': WorkerSerializer(worker).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class WorkerLoginView(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = WorkerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )

        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            worker = Worker.objects.get(user=user)
        except Worker.DoesNotExist:
            return Response(
                {'error': 'This account is not a worker. Please use the client login.'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'worker': WorkerSerializer(worker).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        })


class WorkerProfileView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        try:
            worker = Worker.objects.get(user=request.user)
        except Worker.DoesNotExist:
            return Response(
                {'error': 'Worker profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(WorkerSerializer(worker).data)

    def update(self, request):
        try:
            worker = Worker.objects.get(user=request.user)
        except Worker.DoesNotExist:
            return Response(
                {'error': 'Worker profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()

        # Handle languages from comma-separated string
        languages_raw = data.get('languages', '')
        if isinstance(languages_raw, str) and languages_raw.strip():
            from .models import Language
            lang_names = [n.strip() for n in languages_raw.split(',') if n.strip()]
            lang_ids = []
            for name in lang_names:
                lang = Language.objects.filter(name__iexact=name).first()
                if lang:
                    lang_ids.append(lang.id)
                else:
                    lang = Language.objects.filter(code__iexact=name).first()
                    if lang:
                        lang_ids.append(lang.id)
            # Remove old languages value and set new IDs
            data.pop('languages', None)
            # Set languages as list of IDs directly on the worker
            worker.languages.set(lang_ids)
        elif isinstance(languages_raw, list):
            # Already a list, pass through
            pass
        else:
            data.pop('languages', None)

        # Handle country as empty string
        country = data.get('country', '')
        if country == '' or country is None:
            data.pop('country', None)

        serializer = WorkerUpdateSerializer(worker, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(WorkerSerializer(worker).data)
