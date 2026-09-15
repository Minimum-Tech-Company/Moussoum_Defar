import io
import zipfile
from django.http import StreamingHttpResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Client, Subscription
from .serializers import (
    ClientSerializer, ClientCreateSerializer, SubscriptionSerializer
)
from workers.models import DataCollection, DataSubmission
from workers.serializers import DataCollectionSerializer, DataSubmissionSerializer
from decimal import Decimal


class RegisterView(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        company_name = request.data.get('company_name')

        if not all([username, email, password, company_name]):
            return Response(
                {'error': 'All fields are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already in use'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(password)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        client = Client.objects.create(
            user=user,
            company_name=company_name,
            company_description=request.data.get('company_description', ''),
            website=request.data.get('website', '')
        )

        from django.utils import timezone
        from datetime import timedelta
        Subscription.objects.create(
            client=client,
            plan='free',
            monthly_price=0,
            max_evaluations=5,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=365)
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'client': ClientSerializer(client).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        from django.contrib.auth import authenticate

        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            client = Client.objects.get(user=user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'This account is not a client. Please use the worker login.'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'client': ClientSerializer(client).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        })


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer

    def get_queryset(self):
        return Client.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return ClientCreateSerializer
        return ClientSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        client, created = Client.objects.get_or_create(user=request.user)
        from workers.models import DataCollection, DataSubmission
        collections_count = DataCollection.objects.count()
        submissions_count = DataSubmission.objects.count()
        data = ClientSerializer(client).data
        data['collections_count'] = collections_count
        data['submissions_count'] = submissions_count
        return Response(data)

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        client, created = Client.objects.get_or_create(user=request.user)

        # Handle username update
        username = request.data.get('username', '')
        if username and username != request.user.username:
            from django.contrib.auth.models import User
            if User.objects.filter(username=username).exclude(id=request.user.id).exists():
                return Response(
                    {'error': 'Username already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.username = username
            request.user.save(update_fields=['username'])

        serializer = ClientCreateSerializer(client, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ClientSerializer(client).data)

    @action(detail=False, methods=['get'])
    def usage(self, request):
        client, created = Client.objects.get_or_create(user=request.user)
        return Response({
            'monthly_evaluations': client.monthly_evaluations,
            'max_evaluations': client.max_evaluations,
            'can_evaluate': client.can_evaluate,
            'plan': client.plan,
        })

    @action(detail=False, methods=['get'])
    def subscription(self, request):
        client, created = Client.objects.get_or_create(user=request.user)
        subscription = Subscription.objects.filter(
            client=client, status='active'
        ).first()

        if subscription:
            return Response(SubscriptionSerializer(subscription).data)
        return Response({'error': 'No active subscription'}, status=404)

    @action(detail=False, methods=['post'])
    def upgrade_plan(self, request):
        client, created = Client.objects.get_or_create(user=request.user)
        new_plan = request.data.get('plan')

        if new_plan not in ['free', 'starter', 'pro', 'enterprise']:
            return Response(
                {'error': 'Invalid plan'},
                status=status.HTTP_400_BAD_REQUEST
            )

        plan_configs = {
            'free': {'price': 0, 'evaluations': 5},
            'starter': {'price': 49, 'evaluations': 50},
            'pro': {'price': 199, 'evaluations': 200},
            'enterprise': {'price': 999, 'evaluations': 1000},
        }

        config = plan_configs[new_plan]

        from django.utils import timezone
        from datetime import timedelta

        Subscription.objects.filter(
            client=client, status='active'
        ).update(status='cancelled')

        subscription = Subscription.objects.create(
            client=client,
            plan=new_plan,
            monthly_price=config['price'],
            max_evaluations=config['evaluations'],
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=30)
        )

        client.plan = new_plan
        client.max_evaluations = config['evaluations']
        client.save()

        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=['get'])
    def subscription(self, request):
        client, created = Client.objects.get_or_create(user=request.user)
        subscription = Subscription.objects.filter(
            client=client, status='active'
        ).first()

        if subscription:
            return Response(SubscriptionSerializer(subscription).data)
        return Response({'error': 'No active subscription'}, status=404)


class DataCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = DataCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DataCollection.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        lang_name = data.get('language', '')
        if lang_name and not str(lang_name).isdigit():
            from workers.models import Language
            lang = Language.objects.filter(name__iexact=lang_name).first()
            if lang:
                data['language'] = lang.id

        country_name = data.get('country', '')
        if country_name and not str(country_name).isdigit():
            from workers.models import Country
            country = Country.objects.filter(name__iexact=country_name).first()
            if country:
                data['country'] = country.id

        serializer = DataCollectionSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        collection = serializer.save(created_by=request.user)

        from workers.models import Notification
        Notification.objects.create(
            user=request.user,
            notification_type='collection_ready',
            title='Collection Created',
            message=f'Your data collection "{collection.title}" is now active and ready for workers.',
            data={'collection_id': collection.id}
        )

        return Response(
            DataCollectionSerializer(collection).data,
            status=status.HTTP_201_CREATED
        )


class DataSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = DataSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DataSubmission.objects.select_related(
            'worker__user', 'collection'
        ).order_by('-submitted_at')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        submission = self.get_object()
        if submission.status == 'approved':
            return Response({'detail': 'Already approved'}, status=400)
        submission.status = 'approved'
        submission.reviewed_at = timezone.now()
        submission.reviewer_notes = request.data.get('notes', '')
        score = request.data.get('quality_score')
        if score is not None:
            submission.quality_score = float(score)
        submission.save()

        collection = submission.collection
        collection.current_count += 1
        collection.save()

        worker = submission.worker
        worker.total_tasks += 1
        if submission.quality_score is not None:
            total = worker.total_tasks
            worker.accuracy = ((worker.accuracy * (total - 1)) + submission.quality_score) / total
        worker.save(update_fields=['total_tasks', 'accuracy'])

        from workers.models import QualityLog
        QualityLog.objects.create(
            worker=worker,
            submission=submission,
            score=submission.quality_score or 0.0,
            reviewer=request.user,
            notes=submission.reviewer_notes
        )
        worker.calculate_quality_score()

        Notification.objects.create(
            user=worker.user,
            notification_type='task_completed',
            title='Submission Approved',
            message=f'Your submission to "{collection.title}" was approved!',
            data={'submission_id': submission.id, 'collection_id': collection.id}
        )
        return Response(DataSubmissionSerializer(submission).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        submission = self.get_object()
        if submission.status == 'rejected':
            return Response({'detail': 'Already rejected'}, status=400)
        submission.status = 'rejected'
        submission.reviewed_at = timezone.now()
        submission.reviewer_notes = request.data.get('notes', 'Rejected')
        submission.save()

        from workers.models import Notification
        Notification.objects.create(
            user=submission.worker.user,
            notification_type='task_assigned',
            title='Submission Rejected',
            message=f'Your submission to "{submission.collection.title}" was rejected. {submission.reviewer_notes}',
            data={'submission_id': submission.id}
        )
        return Response(DataSubmissionSerializer(submission).data)

    @action(detail=False, methods=['get'], url_path='download-all')
    def download_all(self, request):
        collection_id = request.query_params.get('collection_id')
        status_filter = request.query_params.get('status')

        if not collection_id:
            return Response({'error': 'collection_id is required'}, status=400)

        try:
            collection = DataCollection.objects.get(id=collection_id)
        except DataCollection.DoesNotExist:
            return Response({'error': 'Collection not found'}, status=404)

        qs = DataSubmission.objects.filter(
            collection=collection, file__isnull=False
        ).exclude(file='')

        if status_filter:
            qs = qs.filter(status=status_filter)

        if not qs.exists():
            return Response({'error': 'No files found in this collection'}, status=404)

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
