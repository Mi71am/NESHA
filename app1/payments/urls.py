from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("history/", views.history, name="history"),
    path("cashier/history/", views.cashier_history, name="cashier_history"),
    path("", views.index, name="index"),
    path("confirm/", views.confirm_payment, name="confirm"),
]
