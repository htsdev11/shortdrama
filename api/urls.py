from django.urls import path

from api.views import AllShortDramaView, ShortDramaByIDView, ShortDramaByNameView, ShortDramaForyouView, \
    ShortDramaForyouByCategoryView

urlpatterns = [
    path("short-drama/",AllShortDramaView.as_view(),),
    path("short-drama/detail/",ShortDramaByIDView.as_view(),),
    path("short-drama/search/",ShortDramaByNameView.as_view(),),
    path("short-drama/foryou/", ShortDramaForyouView.as_view(),),
    path("short-drama/foryou/category/",ShortDramaForyouByCategoryView.as_view(),),
]