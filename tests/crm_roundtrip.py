"""Cross-repository contract tests. ENEPRU_CRM_ROOT must point to the CRM checkout."""
import base64
import importlib.util
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

WEB_ROOT=Path(__file__).resolve().parents[1]
CRM_ROOT=Path(os.environ['ENEPRU_CRM_ROOT']).resolve()
sys.path.insert(0,str(WEB_ROOT));sys.path.insert(0,str(CRM_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.test import TestCase,override_settings
from django.test.runner import DiscoverRunner
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from crm.models import Inquiry,ReceivedMail
from crm.mailbox import import_email,mail_to_inquiry
import crm_bridge
spec=importlib.util.spec_from_file_location('enepru_contract_site',WEB_ROOT/'app.py')
site=importlib.util.module_from_spec(spec);sys.modules[spec.name]=site;spec.loader.exec_module(site)

KEY='contract-test-only-not-a-real-key'

@override_settings(CRM_WEBHOOK_SECRET=KEY,ALLOWED_HOSTS=["testserver"])
class WebsiteContract(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.temp.name);self.override.enable();self.addCleanup(self.override.disable)
        self.admin=get_user_model().objects.create_superuser('contract')
        self.content=json.loads((WEB_ROOT/'content.default.json').read_text())
        self.env=patch.dict(os.environ,{'CRM_SHARED_SECRET':KEY,'CRM_SOURCE_SLUG':'enepru','CRM_ENDPOINT':'https://crm.example.invalid/api/inquiries/enepru/','SMTP_FROM':'web-service@example.invalid','SMTP_HOST':'smtp.example.invalid','SMTP_PORT':'465','SMTP_MODE':'ssl','SMTP_USER':'test','SMTP_PASSWORD':'test-only'})
        self.env.start();self.addCleanup(self.env.stop)
    def payload(self,kind='penb'):
        payload={'kind':kind,'requestId':str(uuid.uuid4()),'name':'Skutečný zákazník z formuláře','email':'customer@example.invalid','phone':'+420000000000','address':'Praha 1','municipality':'Praha','propertyNumber':'12','cadastralArea':'Praha','description':'Rodinný dům','notes':'Prosím zavolat','building':'house','purpose':'sale','size':'0','survey':True,'region':'Vysočina','passport':True,'express':False}
        return payload
    def email(self,payload,files):
        result=site.quote(self.content['pricing'],payload) if payload['kind']=='penb' else None
        with patch('enepru_contract_site.smtplib.SMTP_SSL') as smtp:
            smtp.return_value.__enter__.return_value=smtp.return_value
            smtp.return_value.send_message.return_value={}
            site.send_mail(payload,files,result,self.content)
            return smtp.return_value.send_message.call_args.args[0].as_bytes()
    def test_all_three_forms_email_roundtrip(self):
        for kind,expected in [('penb','both'),('passport','passport'),('contact','other')]:
            with self.subTest(kind=kind):
                payload=self.payload(kind);files=[] if kind=='contact' else [('plan.pdf','application/pdf',b'%PDF-file')]
                mail,_=import_email(self.email(payload,files))
                self.assertTrue(mail.structured_verified)
                self.assertEqual(mail.sender_email,'web-service@example.invalid')
                inquiry=mail_to_inquiry(mail,self.admin)
                self.assertEqual(inquiry.email,payload['email'])
                self.assertEqual(inquiry.name,payload['name'])
                self.assertEqual(inquiry.service,expected)
                self.assertEqual(inquiry.source,'Enepru.cz')
                self.assertEqual(inquiry.attachments.count(),len(files))
                self.assertIn('Prosím zavolat',inquiry.description)
    def test_https_api_and_email_do_not_duplicate_inquiry(self):
        payload=self.payload();files=[('plan.pdf','application/pdf',b'%PDF-file')];result=site.quote(self.content['pricing'],payload)
        def request(req,timeout):
            response=self.client.post('/api/inquiries/enepru/',data=req.data,content_type='application/json',HTTP_X_CRM_TIMESTAMP=req.get_header('X-crm-timestamp'),HTTP_X_CRM_SIGNATURE=req.get_header('X-crm-signature'))
            self.assertIn(response.status_code,[200,201],response.content)
            class Reply:
                status=response.status_code
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def read(self,*args):return response.content
            return Reply()
        with patch('crm_bridge.build_opener') as opener:
            opener.return_value.open.side_effect=request
            first=crm_bridge.send(payload,files,result)
            second=crm_bridge.send(payload,files,result)
        mail,_=import_email(self.email(payload,files));inquiry=mail_to_inquiry(mail,self.admin)
        self.assertEqual(first['id'],second['id']);self.assertEqual(inquiry.pk,first['id'])
        self.assertEqual(Inquiry.objects.count(),1);self.assertEqual(inquiry.attachments.count(),1)
    def test_ten_files_are_transferred_not_silently_dropped(self):
        files=[(f'podklad-{i}.pdf','application/pdf',b'%PDF-'+str(i).encode()) for i in range(10)]
        mail,_=import_email(self.email(self.payload(),files))
        self.assertFalse(mail.skipped_attachments)
        self.assertEqual(mail_to_inquiry(mail,self.admin).attachments.count(),10)
    def test_tampered_mail_signature_does_not_create_customer(self):
        with patch.dict(os.environ,{'CRM_SHARED_SECRET':'wrong-test-key'}):raw=self.email(self.payload(),[])
        mail,_=import_email(raw);self.assertFalse(mail.structured_verified);self.assertTrue(mail.structured_error)
        with self.assertRaises(ValidationError):mail_to_inquiry(mail,self.admin)
        self.assertFalse(Inquiry.objects.exists())
    def test_signed_mail_rejects_modified_attachment(self):
        from email.parser import BytesParser
        from email import policy
        raw=self.email(self.payload(),[('plan.pdf','application/pdf',b'%PDF-original')])
        parsed=BytesParser(policy=policy.default).parsebytes(raw)
        for part in parsed.iter_attachments():
            if part.get_content_type()=='application/pdf':
                part.set_payload(base64.b64encode(b'%PDF-modified').decode())
        record,_=import_email(parsed.as_bytes())
        self.assertTrue(record.structured_verified)
        with self.assertRaises(ValidationError):mail_to_inquiry(record,self.admin)
        self.assertFalse(Inquiry.objects.exists())

    def test_old_website_email_uses_reply_to_not_service_sender(self):
        from email.message import EmailMessage
        mail=EmailMessage();mail['From']='web-service@example.invalid';mail['To']='owner@example.invalid';mail['Reply-To']='customer@example.invalid';mail['Subject']='Nezávazná poptávka – pasport stavby'
        mail.set_content('Jméno: Zákazník\nE-mail: customer@example.invalid\nObec: Brno\nČíslo popisné / parcelní: 12\nPoznámky: Zaměřit')
        record,_=import_email(mail.as_bytes());inquiry=mail_to_inquiry(record,self.admin)
        self.assertEqual(inquiry.email,'customer@example.invalid');self.assertEqual(inquiry.service,'passport')
        self.assertIn('Brno',inquiry.address)

if __name__=='__main__':
    from unittest import TestLoader
    runner=DiscoverRunner(verbosity=2)
    old=runner.setup_databases()
    try:
        result=runner.run_suite(TestLoader().loadTestsFromTestCase(WebsiteContract))
        raise SystemExit(not result.wasSuccessful())
    finally:runner.teardown_databases(old)
