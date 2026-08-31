from django.urls import path
from . import views

urlpatterns = [
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/create/', views.SaleCreateView.as_view(), name='sale_create'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('installments/<int:pk>/pay/', views.InstallmentPayView.as_view(), name='installment_pay'),
]
