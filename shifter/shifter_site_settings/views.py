from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timesince
from django.views.generic import FormView

from shifter_files.models import FileUpload
from shifter_files.tasks import (
    TASK_LOG_LIMIT,
    count_tasks,
    get_task_log,
    get_task_stats,
)

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

            # Save the cleaned value (e.g. "5GB" rather than " 5 gb") and
            # convert booleans to strings for storage.
            value = form.cleaned_data[field.name]
            if isinstance(value, bool):
                value = str(value)  # "True" or "False"

            setting.value = value
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
        context["task_log"] = get_task_log()
        context["task_count"] = count_tasks()
        context["task_log_limit"] = TASK_LOG_LIMIT
        task_stats = get_task_stats()
        context["task_stats"] = task_stats
        if task_stats.last_finished_at:
            last_finished = task_stats.last_finished_at.strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            )
        else:
            last_finished = "Never"

        site_information_lines = [
            "## Site Information",
            "Debug Mode: {}".format(
                "True" if context["debug_mode"] else "False"
            ),
            f"Shifter Version: {context['shifter_version']}",
            f"Python Version: {context['python_version']}",
            f"DB Engine: {context['db_engine']}",
            f"Uptime: {context['uptime']}",
            f"Startup Time: {context['startup_time']}",
            f"Active Files: {context['num_active_files']}",
            f"Expired Files Pending Cleanup: {context['num_expired_files']}",
            f"Tasks Waiting: {task_stats.waiting}",
            f"Tasks Running: {task_stats.running}",
            f"Tasks Scheduled: {task_stats.scheduled}",
            f"Failed Tasks: {task_stats.failed}",
            f"Files Awaiting Hash: {task_stats.files_awaiting_hash}",
            f"Last Task Finished: {last_finished}",
        ]

        context["site_information_clipboard"] = "\n".join(
            site_information_lines
        )

        return context
