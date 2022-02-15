from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


@require_POST
@login_required
def logoutView(request):
    logout(request)
    return redirect("shifter_files:index")
