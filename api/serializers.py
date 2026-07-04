from rest_framework import serializers
from .models import (
    ShortDrama,
    ShortDramaEpisode,
    ShortDramaForyou
)


class ShortDramaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortDrama
        fields = (
            "id",
            "subject_id",
            "title",
            "cover",
            "tags",
            "total_episodes",
            "total_views",
            "description",
            "slug",
        )


class ShortDramaEpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortDramaEpisode
        fields = (
            "id",
            "mini_id",
            "season",
            "episode_number",
            "play_url",
            "thumbnail",
            "duration",
            "width",
            "height",
            "file_size",
            "lock_status",
        )


class ShortDramaDetailSerializer(serializers.ModelSerializer):
    episodes = ShortDramaEpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = ShortDrama
        fields = (
            "id",
            "subject_id",
            "title",
            "cover",
            "tags",
            "total_episodes",
            "total_views",
            "description",
            "slug",
            "episodes",
        )


class ShortDramaForyouSerializer(serializers.ModelSerializer):
    dramas = ShortDramaListSerializer(many=True, read_only=True)

    class Meta:
        model = ShortDramaForyou
        fields = (
            "id",
            "title",
            "order_by",
            "dramas",
        )