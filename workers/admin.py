from django.contrib import admin
from .models import (
    Language, Country, Worker, WorkerLevel,
    DataCollection, DataSubmission, QualityLog
)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'region', 'is_active']
    list_filter = ['is_active', 'region']
    search_fields = ['name', 'code']


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'currency', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    filter_horizontal = ['languages']


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'country', 'level', 'quality_score',
        'total_tasks', 'accuracy', 'is_verified'
    ]
    list_filter = ['level', 'is_verified', 'country']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['quality_score', 'total_tasks', 'accuracy']


@admin.register(WorkerLevel)
class WorkerLevelAdmin(admin.ModelAdmin):
    list_display = ['worker', 'level', 'tasks_required', 'accuracy_required', 'unlocked_at']
    list_filter = ['level']


@admin.register(DataCollection)
class DataCollectionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'data_type', 'language', 'country',
        'target_count', 'current_count', 'status'
    ]
    list_filter = ['data_type', 'status', 'language', 'country']
    search_fields = ['title', 'description']


@admin.register(DataSubmission)
class DataSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'worker', 'collection', 'status', 'quality_score',
        'submitted_at', 'reviewed_at'
    ]
    list_filter = ['status']
    search_fields = ['worker__user__username', 'collection__title']
    readonly_fields = ['submitted_at', 'reviewed_at']


@admin.register(QualityLog)
class QualityLogAdmin(admin.ModelAdmin):
    list_display = ['worker', 'submission', 'score', 'reviewer', 'created_at']
    list_filter = ['created_at']
    search_fields = ['worker__user__username']
