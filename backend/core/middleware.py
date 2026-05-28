from __future__ import annotations

import os
from typing import Callable

from django.http import HttpRequest, HttpResponse


class TenantContextMiddleware:
    """Resolve a tenant for the request and attach it as request.tenant.

    Multi-tenancy is deliberately simple for this prototype:
    - Tenant selected via header `X-Tenant-Slug` (preferred) or query param `tenant`.
    - If absent, falls back to DEFAULT_TENANT_SLUG env var (default: 'demo').

    In a production system you'd likely enforce authentication + tenant membership
    and avoid creating tenants implicitly.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Import lazily to avoid app-loading cycles.
        from core.models import Tenant

        slug = (
            request.headers.get('X-Tenant-Slug')
            or request.GET.get('tenant')
            or os.getenv('DEFAULT_TENANT_SLUG', 'demo')
        )

        tenant = Tenant.objects.filter(slug=slug).first()
        if tenant is None:
            tenant = Tenant.objects.create(slug=slug, name='Demo Tenant')

        request.tenant = tenant  # type: ignore[attr-defined]
        return self.get_response(request)
