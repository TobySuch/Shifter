from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView


class SiteSettingsView(UserPassesTestMixin, TemplateView):
    template_name = "shifter_site_settings/site_settings.html"
    permission_denied_message = "This page is only accessible by super users."

    def test_func(self):
        return self.request.user.is_superuser