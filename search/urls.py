# search/urls.py
from django.urls import path, re_path
from . import views

urlpatterns = [
    path('search/', views.search_files, name='search_files'),
    re_path(r'^open_file/(?P<file_path>.+)/$', views.open_file, name='open_file'),  # Use re_path here
]