from rest_framework import serializers
from .models import (
    ShortDrama,
    ShortDramaEpisode,
    ShortDramaForyou
)


# class ShortDramaListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ShortDrama
#         fields = (
#             "id",
#             "subject_id",
#             "title",
#             "cover",
#             "tags",
#             "total_episodes",
#             "total_views",
#             "description",
#             "slug",
#         )


class ShortDramaListSerializer(serializers.ModelSerializer):
    # thumbnail = serializers.SerializerMethodField()
    first_episode = serializers.SerializerMethodField()

    class Meta:
        model = ShortDrama
        fields = (
            "id",
            "subject_id",
            "title",
            "cover",
            # "thumbnail",
            "tags",
            "total_episodes",
            "first_episode",
            "total_views",
            "description",
            "slug",
        )


    def get_first_episode(self, obj):
        episodes = getattr(obj, "ordered_episodes", [])

        if not episodes:
            return None

        ep = episodes[0]

        return {
            "episode_number": ep.episode_number,
            "play_url": ep.play_url,
            "thumbnail": ep.thumbnail,
            "duration": ep.duration,

        }

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