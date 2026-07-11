from django.core.cache import cache
from django.db.models import Prefetch
from django.shortcuts import render
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.function import BannerService
from api.models import ShortDrama, ShortDramaForyou, ShortDramaEpisode
from api.pagination import CustomPagination
from api.serializers import ShortDramaListSerializer, ShortDramaDetailSerializer, ShortDramaForyouSerializer


CACHE_TIMEOUT = 60 * 60 * 24
class AllShortDramaView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = f"all_short_dramas_{request.GET.urlencode()}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        queryset = (
            ShortDrama.objects.filter(
                is_active=True
            )
            .prefetch_related(
                Prefetch(
                    "episodes",
                    queryset=ShortDramaEpisode.objects.only(
                        "episode_number",
                        "play_url",
                    ).order_by("episode_number"),
                    to_attr="ordered_episodes",
                )
            )
            .order_by("title")
        )

        paginator = CustomPagination()
        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        serializer = ShortDramaListSerializer(
            page,
            many=True,
        )

        response = paginator.get_paginated_response(
            serializer.data
        )
        cache.set(cache_key, response.data, CACHE_TIMEOUT)
        return response

class ShortDramaByIDView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        drama_id = request.GET.get("id")

        if not drama_id:
            return Response(
                {
                    "status": "error",
                    "message": "id is required",
                    "data": {}
                },
                status=400,
            )

        cache_key = f"short_drama_id_{drama_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            drama = ShortDrama.objects.prefetch_related(
                "episodes"
            ).get(
                id=drama_id,
                is_active=True,
            )

            serializer = ShortDramaDetailSerializer(drama)

            response_data = {
                "status": "success",
                "message": "Short drama fetched successfully",
                "data": serializer.data,
            }
            cache.set(cache_key, response_data, CACHE_TIMEOUT)
            return Response(response_data)

        except ShortDrama.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "Short drama not found",
                    "data": {},
                },
                status=404,
            )

class ShortDramaByNameView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        title = request.GET.get("title")

        if not title:
            return Response(
                {
                    "status": "error",
                    "message": "title is required",
                    "data": {},
                },
                status=400,
            )

        cache_key = f"short_drama_name_{title}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            drama = (
                ShortDrama.objects.prefetch_related("episodes")
                .get(
                    title__iexact=title,
                    is_active=True,
                )
            )

            serializer = ShortDramaDetailSerializer(drama)

            response_data = {
                "status": "success",
                "message": "Short drama fetched successfully",
                "data": serializer.data,
            }
            cache.set(cache_key, response_data, CACHE_TIMEOUT)
            return Response(response_data)

        except ShortDrama.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "Short drama not found",
                    "data": {},
                },
                status=404,
            )

class ShortDramaForyouView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = "short_drama_foryou"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        queryset = ShortDramaForyou.objects.prefetch_related(
            "dramas"
        ).filter(
            is_active=True
        ).order_by("order_by")

        serializer = ShortDramaForyouSerializer(
            queryset,
            many=True
        )

        response_data = {
            "status": "success",
            "message": "ForYou fetched successfully",
            "data": serializer.data,
        }
        cache.set(cache_key, response_data, CACHE_TIMEOUT)
        return Response(response_data)

class ShortDramaForyouByCategoryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.GET.get("search")

        if not search:
            return Response(
                {
                    "status": "error",
                    "message": "search parameter is required",
                    "data": {},
                },
                status=400,
            )

        cache_key = f"short_drama_category_{search}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        try:
            queryset = (
                ShortDramaForyou.objects.prefetch_related("dramas")
                .get(
                    title__icontains=search,
                    is_active=True,
                )
            )

            serializer = ShortDramaForyouSerializer(queryset)

            response_data = {
                "status": "success",
                "message": "Category fetched successfully",
                "data": serializer.data,
            }
            cache.set(cache_key, response_data, CACHE_TIMEOUT)
            return Response(response_data)

        except ShortDramaForyou.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "Category not found",
                    "data": {},
                },
                status=404,
            )

class EveryoneWatchingView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        titles = (
            ShortDrama.objects.filter(
                is_active=True,
                is_everyone_search=True,
            )
            .values("title")
        )

        return Response(
            {
                "status": "success",
                "message": None,
                "data": list(titles),
            },
            status=status.HTTP_200_OK,
        )

class HomepageBannerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banners = BannerService.get_banners()

        return Response(
            {
                "success": True,
                "count": len(banners),
                "results": banners,
            },
            status=status.HTTP_200_OK,
        )