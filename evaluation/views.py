from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import (
    AfricanBenchmark, TestCase, Evaluation, TestExecution, APIKey
)
from .serializers import (
    AfricanBenchmarkSerializer, TestCaseSerializer,
    EvaluationSerializer, EvaluationCreateSerializer,
    TestExecutionSerializer, APIKeySerializer
)
from .tasks import evaluate_model


class AfricanBenchmarkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AfricanBenchmark.objects.filter(is_active=True)
    serializer_class = AfricanBenchmarkSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = AfricanBenchmark.objects.filter(is_active=True)
        country = self.request.query_params.get('country')
        category = self.request.query_params.get('category')
        language = self.request.query_params.get('language')

        if country:
            queryset = queryset.filter(country_code=country)
        if category:
            queryset = queryset.filter(category=category)
        if language:
            queryset = queryset.filter(language_code=language)

        return queryset

    @action(detail=True, methods=['get'])
    def tests(self, request, pk=None):
        benchmark = self.get_object()
        test_cases = TestCase.objects.filter(benchmark=benchmark, is_active=True)
        serializer = TestCaseSerializer(test_cases, many=True)
        return Response(serializer.data)


class EvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        return Evaluation.objects.filter(client=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return EvaluationCreateSerializer
        return EvaluationSerializer

    def create(self, request, *args, **kwargs):
        serializer = EvaluationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        benchmark_id = serializer.validated_data['benchmark_id']
        model_name = serializer.validated_data['model_name']
        model_endpoint = serializer.validated_data.get('model_endpoint', '')
        model_api_key = serializer.validated_data.get('model_api_key', '')

        try:
            benchmark = AfricanBenchmark.objects.get(id=benchmark_id, is_active=True)
        except AfricanBenchmark.DoesNotExist:
            return Response(
                {'error': 'Benchmark not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        evaluation = Evaluation.objects.create(
            client=request.user,
            benchmark=benchmark,
            model_name=model_name,
            model_endpoint=model_endpoint,
            model_api_key=model_api_key,
            status='running'
        )

        # Run evaluation asynchronously
        evaluate_model.delay(evaluation.id)

        return Response(
            EvaluationSerializer(evaluation).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        evaluation = self.get_object()
        executions = TestExecution.objects.filter(evaluation=evaluation)

        return Response({
            'evaluation_id': evaluation.id,
            'model_name': evaluation.model_name,
            'benchmark': evaluation.benchmark.name,
            'status': evaluation.status,
            'overall_score': evaluation.score_overall,
            'score_by_category': evaluation.score_by_category,
            'total_tests': evaluation.total_tests,
            'passed_tests': evaluation.passed_tests,
            'failed_tests': evaluation.failed_tests,
            'success_rate': evaluation.success_rate,
            'avg_latency_ms': evaluation.avg_latency_ms,
            'created_at': evaluation.created_at,
            'completed_at': evaluation.completed_at,
        })

    @action(detail=False, methods=['post'])
    def test_quick(self, request):
        serializer = EvaluationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        benchmark_id = serializer.validated_data['benchmark_id']
        model_name = serializer.validated_data['model_name']
        model_endpoint = serializer.validated_data.get('model_endpoint', '')
        model_api_key = serializer.validated_data.get('model_api_key', '')

        try:
            benchmark = AfricanBenchmark.objects.get(id=benchmark_id, is_active=True)
        except AfricanBenchmark.DoesNotExist:
            return Response(
                {'error': 'Benchmark not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create and run quick evaluation
        evaluation = Evaluation.objects.create(
            client=request.user,
            benchmark=benchmark,
            model_name=model_name,
            model_endpoint=model_endpoint,
            model_api_key=model_api_key,
            status='running'
        )

        evaluate_model.delay(evaluation.id)

        return Response(
            EvaluationSerializer(evaluation).data,
            status=status.HTTP_201_CREATED
        )


class APIKeyViewSet(viewsets.ModelViewSet):
    serializer_class = APIKeySerializer

    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        import secrets
        api_key = secrets.token_hex(32)
        serializer.save(user=self.request.user, key=api_key)
