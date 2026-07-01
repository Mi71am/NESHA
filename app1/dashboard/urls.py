from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.customer_dashboard, name="home"),
    path("customer/", views.customer_dashboard, name="customer"),
    path("cashier/", views.cashier_dashboard, name="cashier"),
    path("school/", views.school_representative_dashboard, name="school_representative"),
    path("support/send-urgent-message/", views.send_urgent_message, name="send_urgent_message"),
    path("admin/", views.administrator_dashboard, name="administrator"),
    path("admin/complete-urgent-message/", views.complete_urgent_message, name="complete_urgent_message"),
    path("admin/users/", views.admin_users, name="admin_users"),
    path("admin/monitoring/", views.admin_monitoring, name="admin_monitoring"),
]
