from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timesince
from django.views.generic import FormView

from shifter_files.models import FileUpload

from .forms import SiteSettingsForm
from .models import SiteSetting


class SiteSettingsView(UserPassesTestMixin, FormView):
    template_name = "shifter_site_settings/site_settings.html"
    permission_denied_message = "This page is only accessible by super users."
    form_class = SiteSettingsForm
    success_url = reverse_lazy("shifter_site_settings:site-settings")

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        for field in form:
            setting_name = field.name.split("_", maxsplit=1)[1]
            setting = SiteSetting.objects.get(name=setting_name)
            setting.value = field.value()
            setting.save()

        context = self.get_context_data()
        context["message"] = "Settings Saved!"
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["debug_mode"] = bool(settings.DEBUG)
        context["shifter_version"] = settings.SHIFTER_VERSION
        context["python_version"] = settings.PYTHON_VERSION
        context["db_engine"] = settings.DB_OPTION.upper()
        context["uptime"] = timesince.timesince(settings.STARTUP_TIME, depth=1)
        context["startup_time"] = settings.STARTUP_TIME.strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )
        context["num_active_files"] = (
            FileUpload.get_non_expired_files().count()
        )
        context["num_expired_files"] = FileUpload.get_expired_files().count()

        return context
