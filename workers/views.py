from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from .models import (
    Language, Country, Worker, WorkerLevel,
    DataCollection, DataSubmission, QualityLog,
    AnnotationTask, AnnotationResult, RLHFTask, RLHFFeedback,
    SyntheticDataJob, Notification
)
from .serializers import (
    LanguageSerializer, CountrySerializer, WorkerSerializer,
    WorkerCreateSerializer, WorkerScoreSerializer,
    DataCollectionSerializer, DataSubmissionSerializer,
    QualityLogSerializer, AnnotationTaskSerializer, AnnotationResultSerializer,
    RLHFTaskSerializer, RLHFFeedbackSerializer, SyntheticDataJobSerializer,
    NotificationSerializer
)


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.filter(is_active=True)
    serializer_class = LanguageSerializer
    permission_classes = [permissions.AllowAny]


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]


class WorkerViewSet(viewsets.ModelViewSet):
    serializer_class = WorkerSerializer

    def get_queryset(self):
        return Worker.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return WorkerCreateSerializer
        return WorkerSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        worker, created = Worker.objects.get_or_create(user=request.user)
        serializer = WorkerSerializer(worker)
        return Response(serializer.data)

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        worker, created = Worker.objects.get_or_create(user=request.user)
        serializer = WorkerCreateSerializer(worker, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(WorkerSerializer(worker).data)

    @action(detail=False, methods=['get'])
    def score(self, request):
        worker, created = Worker.objects.get_or_create(user=request.user)
        worker.calculate_quality_score()
        serializer = WorkerScoreSerializer(worker)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def tasks(self, request):
        worker, created = Worker.objects.get_or_create(user=request.user)
        submissions = DataSubmission.objects.filter(worker=worker)
        serializer = DataSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        workers = Worker.objects.select_related('user', 'country').order_by('-quality_score')[:20]
        data = []
        for i, w in enumerate(workers):
            photo_url = w.profile_photo.url if w.profile_photo else None
            data.append({
                'id': w.id,
                'rank': i + 1,
                'username': w.user.username,
                'country': w.country.name if w.country else '',
                'quality_score': w.quality_score,
                'total_tasks': w.total_tasks,
                'level': w.level,
                'profile_photo': photo_url,
            })
        return Response(data)


class PublicWorkerView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            worker = Worker.objects.select_related('user', 'country').get(pk=pk)
        except Worker.DoesNotExist:
            return Response({'error': 'Worker not found'}, status=404)
        serializer = WorkerSerializer(worker)
        return Response(serializer.data)


class DataCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DataCollection.objects.filter(status='active')
    serializer_class = DataCollectionSerializer

    def get_queryset(self):
        queryset = DataCollection.objects.filter(status='active')
        data_type = self.request.query_params.get('data_type')
        language = self.request.query_params.get('language')
        country = self.request.query_params.get('country')

        if data_type:
            queryset = queryset.filter(data_type=data_type)
        if language:
            queryset = queryset.filter(language__code=language)
        if country:
            queryset = queryset.filter(country__code=country)

        return queryset

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        collection = self.get_object()
        worker, created = Worker.objects.get_or_create(user=request.user)

        serializer = DataSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(worker=worker, collection=collection)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        collection = self.get_object()
        status_filter = request.query_params.get('status')

        qs = DataSubmission.objects.filter(
            collection=collection, file__isnull=False
        ).exclude(file='')

        if status_filter:
            qs = qs.filter(status=status_filter)

        if not qs.exists():
            return Response({'error': 'No files found in this collection'}, status=404)

        import io
        import zipfile
        from django.http import StreamingHttpResponse

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for sub in qs:
                if sub.file:
                    try:
                        filename = sub.file.name
                        content = sub.file.read()
                        zf.writestr(filename, content)
                    except Exception:
                        continue

        zip_buffer.seek(0)
        response = StreamingHttpResponse(zip_buffer, content_type='application/zip')
        safe_title = collection.title.replace(' ', '_')[:50]
        response['Content-Disposition'] = f'attachment; filename="{safe_title}.zip"'
        return response


class DataSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = DataSubmissionSerializer

    def get_queryset(self):
        return DataSubmission.objects.filter(worker__user=self.request.user)

    def perform_create(self, serializer):
        worker, created = Worker.objects.get_or_create(user=self.request.user)
        serializer.save(worker=worker)


# === HELPER ===

def resolve_names_to_ids(data):
    """Resolve language and country names to IDs in request data."""
    from .models import Language, Country
    lang = data.get('language', '')
    if lang and not str(lang).isdigit():
        obj = Language.objects.filter(name__iexact=lang).first()
        if obj:
            data['language'] = obj.id
    country = data.get('country', '')
    if country and not str(country).isdigit():
        obj = Country.objects.filter(name__iexact=country).first()
        if obj:
            data['country'] = obj.id
    return data


# === ANNOTATION TASKS ===

class AnnotationTaskViewSet(viewsets.ModelViewSet):
    serializer_class = AnnotationTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = AnnotationTask.objects.all()
        if self.action == 'list' and self.request.query_params.get('available'):
            queryset = queryset.filter(status='in_progress')
        task_type = self.request.query_params.get('task_type')
        language = self.request.query_params.get('language')
        country = self.request.query_params.get('country')
        difficulty = self.request.query_params.get('difficulty')

        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if language:
            queryset = queryset.filter(language__code=language)
        if country:
            queryset = queryset.filter(country__code=country)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        return queryset

    def create(self, request, *args, **kwargs):
        data = resolve_names_to_ids(request.data.copy())
        serializer = AnnotationTaskSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(created_by=request.user)

        Notification.objects.create(
            user=request.user,
            notification_type='task_assigned',
            title='Annotation Task Created',
            message=f'New annotation task "{task.title}" is ready for workers.',
            data={'task_id': task.id}
        )

        return Response(AnnotationTaskSerializer(task).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        if task.current_annotations >= task.max_annotations:
            return Response({'error': 'Task is full'}, status=status.HTTP_400_BAD_REQUEST)
        task.current_annotations += 1
        if task.current_annotations >= task.max_annotations:
            task.status = 'completed'
        task.save()
        return Response(AnnotationTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def submit_annotation(self, request, pk=None):
        task = self.get_object()
        worker, _ = Worker.objects.get_or_create(user=request.user)

        existing = AnnotationResult.objects.filter(task=task, worker=worker).first()
        if existing:
            return Response({'error': 'Already submitted'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AnnotationResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save(task=task, worker=worker)

        worker.total_tasks += 1
        worker.save(update_fields=['total_tasks'])

        Notification.objects.create(
            user=request.user,
            notification_type='task_completed',
            title='Annotation Complete',
            message=f'You completed annotation: {task.title}',
            data={'task_id': task.id}
        )

        return Response(AnnotationResultSerializer(result).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_results(self, request):
        worker, _ = Worker.objects.get_or_create(user=request.user)
        results = AnnotationResult.objects.filter(worker=worker)
        serializer = AnnotationResultSerializer(results, many=True)
        return Response(serializer.data)


# === RLHF TASKS ===

class RLHFTaskViewSet(viewsets.ModelViewSet):
    serializer_class = RLHFTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = RLHFTask.objects.all()
        if self.action == 'list' and self.request.query_params.get('available'):
            queryset = queryset.filter(status='in_progress')
        task_type = self.request.query_params.get('task_type')
        language = self.request.query_params.get('language')
        country = self.request.query_params.get('country')

        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if language:
            queryset = queryset.filter(language__code=language)
        if country:
            queryset = queryset.filter(country__code=country)

        return queryset

    def create(self, request, *args, **kwargs):
        data = resolve_names_to_ids(request.data.copy())
        serializer = RLHFTaskSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(created_by=request.user)

        Notification.objects.create(
            user=request.user,
            notification_type='task_assigned',
            title='RLHF Task Created',
            message=f'New RLHF task "{task.title}" is ready for workers.',
            data={'task_id': task.id}
        )

        return Response(RLHFTaskSerializer(task).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        if task.current_workers >= task.max_workers:
            return Response({'error': 'Task is full'}, status=status.HTTP_400_BAD_REQUEST)
        task.current_workers += 1
        if task.current_workers >= task.max_workers:
            task.status = 'completed'
        task.save()
        return Response(RLHFTaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def submit_feedback(self, request, pk=None):
        task = self.get_object()
        worker, _ = Worker.objects.get_or_create(user=request.user)

        existing = RLHFFeedback.objects.filter(task=task, worker=worker).first()
        if existing:
            return Response({'error': 'Already submitted'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RLHFFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save(task=task, worker=worker)

        worker.total_tasks += 1
        worker.save(update_fields=['total_tasks'])

        Notification.objects.create(
            user=request.user,
            notification_type='task_completed',
            title='RLHF Feedback Complete',
            message=f'You completed feedback for: {task.title}',
            data={'task_id': task.id}
        )

        return Response(RLHFFeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_feedbacks(self, request):
        worker, _ = Worker.objects.get_or_create(user=request.user)
        feedbacks = RLHFFeedback.objects.filter(worker=worker)
        serializer = RLHFFeedbackSerializer(feedbacks, many=True)
        return Response(serializer.data)


# === SYNTHETIC DATA ===

class SyntheticDataJobViewSet(viewsets.ModelViewSet):
    serializer_class = SyntheticDataJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SyntheticDataJob.objects.all()

    def create(self, request, *args, **kwargs):
        data = resolve_names_to_ids(request.data.copy())
        serializer = SyntheticDataJobSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save(created_by=request.user)

        Notification.objects.create(
            user=request.user,
            notification_type='task_assigned',
            title='Synthetic Data Job Created',
            message=f'Synthetic data generation "{job.title}" has been started.',
            data={'job_id': job.id}
        )

        return Response(SyntheticDataJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        job = self.get_object()
        if job.status != 'completed':
            return Response({'error': 'Job not completed yet'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'title': job.title,
            'type': job.generation_type,
            'count': job.current_count,
            'data': job.output_data
        })


# === NOTIFICATIONS ===

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'count': count})
