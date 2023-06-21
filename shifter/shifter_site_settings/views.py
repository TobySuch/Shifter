from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import FormView
from django.urls import reverse_lazy
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
        return super().form_valid(form)
