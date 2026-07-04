from django.shortcuts import render
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import ShortDrama, ShortDramaForyou
from api.pagination import CustomPagination
from api.serializers import ShortDramaListSerializer, ShortDramaDetailSerializer, ShortDramaForyouSerializer


# Create your views here.
class AllShortDramaView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = ShortDrama.objects.filter(
            is_active=True
        ).order_by("title")

        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ShortDramaListSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


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

        try:
            drama = ShortDrama.objects.prefetch_related(
                "episodes"
            ).get(
                id=drama_id,
                is_active=True,
            )

            serializer = ShortDramaDetailSerializer(drama)

            return Response(
                {
                    "status": "success",
                    "message": "Short drama fetched successfully",
                    "data": serializer.data,
                }
            )

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

        try:
            drama = (
                ShortDrama.objects.prefetch_related("episodes")
                .get(
                    title__iexact=title,
                    is_active=True,
                )
            )

            serializer = ShortDramaDetailSerializer(drama)

            return Response(
                {
                    "status": "success",
                    "message": "Short drama fetched successfully",
                    "data": serializer.data,
                }
            )

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
        queryset = ShortDramaForyou.objects.prefetch_related(
            "dramas"
        ).filter(
            is_active=True
        ).order_by("order_by")

        serializer = ShortDramaForyouSerializer(
            queryset,
            many=True
        )

        return Response(
            {
                "status": "success",
                "message": "ForYou fetched successfully",
                "data": serializer.data,
            }
        )

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

        try:
            queryset = (
                ShortDramaForyou.objects.prefetch_related("dramas")
                .get(
                    title__icontains=search,
                    is_active=True,
                )
            )

            serializer = ShortDramaForyouSerializer(queryset)

            return Response(
                {
                    "status": "success",
                    "message": "Category fetched successfully",
                    "data": serializer.data,
                }
            )

        except ShortDramaForyou.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "Category not found",
                    "data": {},
                },
                status=404,
            )