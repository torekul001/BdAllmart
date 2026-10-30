import io
import unittest
from unittest.mock import patch
import app as web
import course_service as service
from course_content import sanitize_course_content

COURSE = dict(Id=7, Name='Graphic Design', Course='Graphic Design', CourseCategory='Graphic Design', VideoLink='abcdefghijk', ContentHtml='<h2>Learn design</h2><img src="/static/course-images/example.png"><iframe src="https://www.youtube.com/embed/abcdefghijk"></iframe>')

class CourseContentTests(unittest.TestCase):
    def setUp(self):
        web.app.config['TESTING'] = True
        self.client = web.app.test_client()
    def test_sanitizer(self):
        content = sanitize_course_content(COURSE['ContentHtml'] + '<script>alert(1)</script><img src="javascript:alert(1)" onerror="alert(1)"><iframe src="https://evil.example"></iframe><a href="javascript:alert(1)">click</a>')
        self.assertIn('<h2>Learn design</h2>', content)
        self.assertIn('https://www.youtube.com/embed/abcdefghijk', content)
        for unsafe in ['<script', 'onerror', 'javascript:', 'evil.example']:
            self.assertNotIn(unsafe, content)
    def test_insert_and_update(self):
        with patch.object(service, 'ensure_course_category_column'), patch.object(service, 'ensure_course_content_column'), patch.object(service, 'execute') as execute:
            service.add_course_video('Graphic Design', 'Lesson', 'abcdefghijk', '<b>Content</b>')
            self.assertIn('INSERT INTO', execute.call_args.args[0])
            self.assertEqual(execute.call_args.args[1][-1], '<b>Content</b>')
            service.add_course_video('Graphic Design', 'Lesson', 'abcdefghijk', '<b>Updated</b>', 7)
            self.assertIn('UPDATE ClassVideo', execute.call_args.args[0])
            self.assertEqual(execute.call_args.args[1][-1], 7)
            with self.assertRaises(ValueError):
                service.add_course_video('Design', 'Lesson', 'invalid')
    def test_public_details_and_missing_course(self):
        with patch.object(web, 'get_public_course_video', return_value=COURSE.copy()):
            response = self.client.get('/training/7')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Learn design', response.data)
            self.assertIn(b'/static/course-images/example.png', response.data)
            self.assertIn(b'learning-video-player', response.data)
            self.assertIn(b'https://www.youtube.com/embed/abcdefghijk', response.data)
        with patch.object(web, 'get_public_course_video', return_value=None):
            self.assertEqual(self.client.get('/training/999').status_code, 404)
    def test_training_subcategory(self):
        with patch.object(web, 'get_category_details', return_value={'id':'6','name':'IT Service'}), patch.object(web, 'get_subcategory_details', return_value={'id':'78','name':'Training'}), patch.object(web, 'get_category_products', return_value=[]), patch.object(web, 'get_category_shortcuts', return_value=[]), patch.object(web, 'get_public_course_videos', return_value=[COURSE]):
            response = self.client.get('/category/6?sub=78')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'/training/7', response.data)
            self.assertIn(b'Graphic Design', response.data)
    def test_upload_authorization_and_validation(self):
        self.assertEqual(self.client.post('/courses/content-image').status_code, 302)
        with self.client.session_transaction() as session:
            session['user_id']='1'
            session['category']='Institute'
        response = self.client.post('/courses/content-image', data={'image': (io.BytesIO(b'<svg onload="alert(1)">'), 'unsafe.svg')})
        self.assertEqual(response.status_code, 400)
    def test_templates_compile(self):
        for name in ['course_manage.html','training_details.html','_training_courses.html','category_products.html','login.html']:
            web.app.jinja_env.get_template(name)

    def test_save_large_course_content(self):
        with self.client.session_transaction() as session:
            session['user_id'] = '1'
            session['category'] = 'Institute'
        content = '<p>' + ('Course description. ' * 40000) + '</p>'
        self.assertGreater(len(content.encode()), 500000)
        with patch.object(web, 'get_public_course_video', return_value=COURSE.copy()), patch.object(web, 'add_course_video') as save:
            response = self.client.post('/courses/manage?edit=7', data={
                'video_id': '7', 'category': 'Graphic Design', 'title': 'Lesson',
                'youtube_link': 'abcdefghijk', 'content_html': content,
            })
            self.assertEqual(response.status_code, 302)
            self.assertEqual(save.call_args.args[3], content)
            self.assertEqual(save.call_args.args[4], 7)

if __name__ == '__main__':
    unittest.main(verbosity=2)
