from django.urls import path

from . import views

app_name = "beneficiaries"

urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register, name="register"),
    path("admin/", views.admin_beneficiaries, name="admin_list"),
    path("<int:beneficiary_id>/", views.beneficiary_detail, name="detail"),
    path("pending/", views.pending_questionnaires, name="pending"),
    path("pending/<int:beneficiary_id>/resume/", views.resume_questionnaire, name="resume"),
    path("view/", views.view_beneficiaries, name="view"),
    path("reassess/", views.reassess_beneficiaries, name="reassess"),
    path("reassess/<int:beneficiary_id>/form/", views.reassessment_form, name="reassess_form"),
]
