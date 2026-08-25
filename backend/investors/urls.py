from django.urls import path

from .views import InvestorDocumentsView

urlpatterns = [
    path("investor-documents/", InvestorDocumentsView.as_view(), name="investor-documents"),
]
