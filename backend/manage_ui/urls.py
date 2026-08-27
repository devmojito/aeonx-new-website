from django.urls import path

from . import api, blog_api, views

app_name = "manage"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("documents/", views.documents, name="documents"),
    path("enquiries/", views.submissions, name="submissions"),
    path("categories/", views.taxonomy, name="taxonomy"),
    path("blog/", views.blog, name="blog"),
    path("announcement/", views.announcement, name="announcement"),

    # JSON, consumed only by static/manage/app.js
    path("api/stats/", api.stats, name="api-stats"),
    path("api/announcement/", api.announcement, name="api-announcement"),
    path("api/taxonomy/", api.taxonomy, name="api-taxonomy"),
    path("api/categories/", api.category_detail, name="api-category-create"),
    path("api/categories/<int:pk>/", api.category_detail, name="api-category-detail"),
    path("api/documents/", api.document_list, name="api-documents"),
    path("api/documents/create/", api.document_create, name="api-document-create"),
    path("api/documents/bulk/", api.document_bulk, name="api-document-bulk"),
    path("api/documents/<int:pk>/", api.document_update, name="api-document-update"),
    path("api/documents/<int:pk>/delete/", api.document_delete, name="api-document-delete"),
    path("api/enquiries/", api.submission_list, name="api-submissions"),
    path("api/enquiries/export/", api.submission_export, name="api-submissions-export"),
    path("api/enquiries/<int:pk>/", api.submission_update, name="api-submission-update"),

    path("api/blog/", blog_api.post_list, name="api-posts"),
    path("api/blog/stats/", blog_api.blog_stats, name="api-blog-stats"),
    path("api/blog/create/", blog_api.post_save, name="api-post-create"),
    path("api/blog/image/", blog_api.body_image_upload, name="api-post-image"),
    path("api/blog/<int:pk>/", blog_api.post_detail, name="api-post-detail"),
    path("api/blog/<int:pk>/save/", blog_api.post_save, name="api-post-save"),
    path("api/blog/<int:pk>/delete/", blog_api.post_delete, name="api-post-delete"),
]
