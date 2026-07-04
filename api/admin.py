from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    ShortDrama,
    ShortDramaEpisode,
    ShortDramaForyou,
)


class ShortDramaEpisodeInline(admin.TabularInline):
    model = ShortDramaEpisode
    extra = 0
    show_change_link = True
    can_delete = False

    fields = (
        "episode_number",
        "season",
        "duration",
        "lock_status",
        "is_active",
    )

    readonly_fields = fields

    ordering = ("episode_number",)


@admin.register(ShortDramaEpisode)
class ShortDramaEpisodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "drama",
        "episode_number",
        "season",
        "duration",
        "lock_status",
        "is_active",
    )

    search_fields = (
        "drama__title",
        "mini_id",
        "subject_id",
    )

    list_filter = (
        "is_active",
        "season",
        "lock_status",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "drama",
        "episode_number",
    )


@admin.register(ShortDrama)
class ShortDramaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "subject_id",
        "slug",
        "total_episodes",
        "episode_count",
        "is_active",
    )

    search_fields = (
        "title",
        "subject_id",
        "slug",
    )

    list_filter = (
        "is_active",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [ShortDramaEpisodeInline]

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "title",
                "subject_id",
                "slug",
                "cover",
                "description",
                "tags",
                "total_episodes",
                "total_views",
                "is_active",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def episode_count(self, obj):
        return obj.episodes.count()

    episode_count.short_description = "Episodes"


@admin.register(ShortDramaForyou)
class ShortDramaForyouAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "drama_count",
        "order_by",
        "is_active",
        "last_update",
    )

    search_fields = (
        "title",
    )

    list_filter = (
        "is_active",
    )

    filter_horizontal = (
        "dramas",
    )

    readonly_fields = (
        "last_update",
    )

    ordering = (
        "order_by",
    )

    def drama_count(self, obj):
        return obj.dramas.count()

    drama_count.short_description = "Total Dramas"