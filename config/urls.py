from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache

admin.site.site_header = "NTUB個人課表 · 管理後台"
admin.site.site_title = "NTUB個人課表"
admin.site.index_title = "系統管理中樞"
admin.site.site_url = None


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except DatabaseError:
        return HttpResponse('database unavailable', status=503, content_type='text/plain')
    return HttpResponse('ok', content_type='text/plain')

urlpatterns = [
    path('healthz/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('school/', include('courses.school_urls')),
    path('sw.js', never_cache(TemplateView.as_view(template_name='sw.js', content_type='application/javascript')), name='service_worker'),
    path('manifest.json', never_cache(TemplateView.as_view(template_name='manifest.json', content_type='application/manifest+json')), name='pwa_manifest'),
    path('accounts/', include('accounts.urls')),
    path('selection/', include('selection.urls')),
    path('captcha/', include('captcha.urls')),
    path('', include('courses.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
