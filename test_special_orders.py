"""Special-order validation without creating real customer orders."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import app

class SpecialOrderTest(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        self.temp=tempfile.TemporaryDirectory()
        self.directory=Path(self.temp.name)
        self.services=patch('special_orders.service_types',return_value=[{'Services':'Web Design'}]);self.services.start()
        self.save=patch('special_orders.execute');self.write=self.save.start()
        self.config=patch.dict(app.config,MARKET_PRIVATE_DIR=self.temp.name);self.config.start()
        with self.client.session_transaction() as session:
            session['market_csrf']='test-token'

    def tearDown(self):
        self.config.stop();self.save.stop();self.services.stop();self.temp.cleanup()

    def submit(self,**changes):
        data={'csrf_token':'test-token','details':"Build my client's website",'email':'buyer@example.com','service_type':'Web Design'}
        data.update(changes)
        return self.client.post('/special-order',data=data)

    def test_guest_request_uses_original_order_table_and_parameterized_values(self):
        response=self.submit()
        self.assertEqual(response.status_code,302)
        self.assertTrue(response.location.endswith('/login#jobs'))
        sql,params=self.write.call_args.args
        self.assertIn('INSERT INTO OrderNow',sql)
        self.assertNotIn("client's",sql)
        self.assertEqual(params[1],"Build my client's website")
        self.assertEqual(params[5],'Web Design')

    def test_invalid_fields_and_csrf_do_not_save(self):
        for changes in [{'email':'bad'},{'details':''},{'service_type':'Forged'}]:
            self.submit(**changes)
        self.assertEqual(self.submit(csrf_token='forged').status_code,400)
        self.write.assert_not_called()

    def test_samples_are_private_and_fit_legacy_columns(self):
        self.submit(image=(io.BytesIO(b'\x89PNG\r\n\x1a\nexample'),'sample.png'),asset=(io.BytesIO(b'%PDF-example'),'brief.pdf'))
        params=self.write.call_args.args[1]
        for path in params[2:4]:
            self.assertLessEqual(len(path),50)
            self.assertTrue((self.directory/path.split('/')[-1]).exists())
            self.assertEqual(self.client.get(path).status_code,403)

    def test_bad_second_upload_removes_first_orphan(self):
        self.submit(image=(io.BytesIO(b'\x89PNG\r\n\x1a\nexample'),'sample.png'),asset=(io.BytesIO(b'bad'),'brief.exe'))
        self.write.assert_not_called()
        self.assertEqual(list(self.directory.iterdir()),[])

    def test_sample_download_requires_owner_or_admin(self):
        self.submit(asset=(io.BytesIO(b'%PDF-example'),'brief.pdf'))
        path=self.write.call_args.args[1][3]
        with self.client.session_transaction() as session:
            session['user_id']='test-user'
        account={'Email':'other@example.com','UserCatagory':'Customer','Active':'1','Status':'True'}
        with patch('special_orders.fetch_one',side_effect=[account,{'email':'buyer@example.com'}]):
            self.assertEqual(self.client.get(path).status_code,403)
        account['Email']='buyer@example.com'
        with patch('special_orders.fetch_one',side_effect=[account,{'email':'buyer@example.com'}]):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            response.close()
