from django.test import override_settings

# Run tasks synchronously when they are enqueued. Tasks are enqueued with
# transaction.on_commit, so wrap the code under test in
# self.captureOnCommitCallbacks(execute=True) as well.
immediate_tasks = override_settings(
    TASKS={
        "default": {
            "BACKEND": "django.tasks.backends.immediate.ImmediateBackend"
        }
    }
)
