from pathlib import Path
import json
import re
from django.test import SimpleTestCase
from django.contrib.staticfiles import finders
from django.conf import settings

ROOT = settings.BASE_DIR

class FrontendHostTests(SimpleTestCase):
    def test_every_page_can_be_opened_directly_without_a_database(self):
        routes = ["/", "/accounts/login/", "/accounts/register/", "/accounts/profile/", "/accounts/connections/", "/accounts/roles/", "/accounts/profile/friend-1/", "/accounts/groups/group-1/", "/selection/timetable/", "/selection/timetable/print/", "/selection/timetable/student/friend-1/", "/selection/calendar/", "/selection/calendar/?view=week", "/selection/calendar/?view=day", "/selection/calendar/?view=list", "/selection/calendar/events/new/", "/selection/calendar/events/example/", "/selection/import/excel/", "/selection/prelist/", "/selection/results/", "/selection/console/", "/selection/console/offerings/", "/courses/browse/", "/timetables/classes/", "/school/", "/school/login/", "/school/classes/", "/school/offerings/", "/school/courses/", "/school/students/import/", "/admin/", "/admin/login/", "/demo/storage/"]
        for url in routes:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '/static/demo/app.mjs')
                self.assertNotIn('Set-Cookie', response.headers)

    def test_every_course_detail_and_roster_url_is_reachable(self):
        catalog = json.loads((ROOT / 'static/demo/catalog.json').read_text(encoding='utf-8'))
        for course in catalog['offerings']:
            for prefix in ('/courses/offering/', '/school/offerings/'):
                self.assertEqual(self.client.get(f"{prefix}{course['id']}/").status_code, 200)
                self.assertEqual(self.client.get(f"{prefix}{course['id']}/roster/").status_code, 200)

    def test_all_shell_assets_and_module_dependencies_exist(self):
        shell = self.client.get('/').content.decode()
        assets = re.findall(r'(?:src|href)="(/static/[^"?]+)', shell)
        for path in assets:
            self.assertIsNotNone(finders.find(path.removeprefix('/static/')), path)
        for filename in ('app.mjs', 'model.mjs', 'import.mjs', 'routes.mjs'):
            source = (ROOT / 'static/demo' / filename).read_text(encoding='utf-8')
            for imported in re.findall(r"from ['\"]\./([^'\"]+)", source):
                self.assertTrue((ROOT / 'static/demo' / imported).is_file(), imported)
        for name in ('demo/import-worker.js', 'demo/catalog.json', 'vendor/xlsx.full.min.js'):
            self.assertIsNotNone(finders.find(name))

    def test_host_never_accepts_backend_mutations(self):
        for url in ('/accounts/login/', '/selection/course/1/add/', '/selection/import/excel/', '/school/students/import/', '/admin/'):
            self.assertEqual(self.client.post(url, {'password':'not-real'}).status_code, 405)
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.dummy')
        self.assertEqual(self.client.get('/healthz/').content, b'ok')

    def test_startup_files_and_assets_are_committable_and_complete(self):
        self.assertEqual(len(list((ROOT / 'bat').glob('*.bat'))), 2)
        self.assertTrue((ROOT / 'bat/commands.txt').is_file())
        self.assertFalse((ROOT / 'README.md').exists())
        self.assertTrue((ROOT / 'reference/mid/selection/services.py').is_file())
        self.assertEqual((ROOT / 'requirements.txt').read_text().strip(), 'Django==5.2.17')
        for path in (ROOT / 'bat').glob('*.bat'):
            self.assertIn(b'\r\n', path.read_bytes())
