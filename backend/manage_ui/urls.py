from django.urls import path

from . import api, views

app_name = "manage"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("documents/", views.documents, name="documents"),
    path("enquiries/", views.submissions, name="submissions"),
    path("categories/", views.taxonomy, name="taxonomy"),

    # JSON, consumed only by static/manage/app.js
    path("api/stats/", api.stats, name="api-stats"),
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
]
