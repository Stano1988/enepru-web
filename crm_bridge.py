"""ENEPRU → CRM contract. No secrets or customer data in browser JavaScript."""
import base64
import hashlib
import hmac
import json
import os
import ssl
import time
import uuid
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler

SCHEMA = 'enepru.inquiry.v1'
MIME = 'application/vnd.enepru.inquiry+json'
FILENAME = 'enepru-poptavka.json'


def inquiry_data(payload,result=None):
    kind=payload['kind']
    service='both' if kind=='penb' and payload.get('passport') else {'penb':'penb','passport':'passport','contact':'other'}[kind]
    address=payload.get('address','').strip()
    if not address and kind=='passport':
        address=', '.join(value for value in [payload.get('municipality',''),payload.get('propertyNumber',''),payload.get('cadastralArea','')] if value and value!='—')
    labels={'building':'Typ stavby','purpose':'Účel','size':'Rozsah','survey':'Zaměření','region':'Kraj','passport':'Také pasport','express':'Expres','municipality':'Obec','propertyNumber':'Číslo stavby / parcela','cadastralArea':'Katastrální území','description':'Popis stavby','notes':'Požadavek'}
    description='\n'.join(f'{label}: {payload[key]}' for key,label in labels.items() if payload.get(key) not in (None,''))
    if result:description+='\n\nOrientační kalkulace webu: '+json.dumps(result,ensure_ascii=False)+'. Konečná nabídka vyžaduje kontrolu.'
    return {'schema':SCHEMA,'external_id':str(uuid.UUID(payload['requestId'])),'source_slug':os.environ.get('CRM_SOURCE_SLUG','enepru'),'name':payload['name'],'email':payload['email'],'phone':payload.get('phone',''),'address':address,'service':service,'description':description or 'Dotaz z webu','source_details':{'form':kind,'building':payload.get('building'),'purpose':payload.get('purpose'),'region':payload.get('region'),'size':payload.get('size'),'survey':payload.get('survey'),'express':payload.get('express'),'quote':result}}


def envelope(payload,result=None,attachments=None):
    data=inquiry_data(payload,result)
    data['attachment_manifest']=[{'name':name,'sha256':hashlib.sha256(content).hexdigest()} for name,mime,content in (attachments or [])]
    return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def sign_email(content):
    key=os.environ.get('CRM_SHARED_SECRET','')
    return hmac.new(key.encode(),content,hashlib.sha256).hexdigest() if key else ''


def ready():
    endpoint=os.environ.get('CRM_ENDPOINT','')
    p=urlsplit(endpoint)
    return bool(p.scheme=='https' and p.hostname and not p.username and not p.password and not p.fragment and os.environ.get('CRM_SHARED_SECRET'))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def send(payload,attachments,result=None):
    if not ready():raise ValueError('Přímé CRM připojení není bezpečně nastavené.')
    data=inquiry_data(payload,result)
    data['attachments']=[{'name':name,'content':base64.b64encode(content).decode('ascii'),'sha256':hashlib.sha256(content).hexdigest()} for name,mime,content in attachments]
    raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    stamp=str(int(time.time()))
    signature=hmac.new(os.environ['CRM_SHARED_SECRET'].encode(),stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    request=Request(os.environ['CRM_ENDPOINT'],data=raw,headers={'Content-Type':'application/json','X-CRM-Timestamp':stamp,'X-CRM-Signature':signature},method='POST')
    opener=build_opener(NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))
    with opener.open(request,timeout=12) as response:
        body=json.loads(response.read(65536))
        if response.status not in (200,201) or not isinstance(body.get('id'),int):raise ValueError('CRM nepotvrdilo přijetí.')
    return body


def pending_body(payload,attachments,result):
    return json.dumps({'payload':payload,'files':[{'name':name,'mime':mime,'body':base64.b64encode(content).decode('ascii')} for name,mime,content in attachments],'result':result},ensure_ascii=False)


def retry_pending(db,lock):
    if not ready():return 0
    with db() as connection:
        rows=connection.execute('SELECT id,body,attempts FROM crm_pending WHERE next_attempt<=? ORDER BY next_attempt LIMIT 10',(int(time.time()),)).fetchall()
    sent=0
    for request_id,body,attempts in rows:
        # Claim in SQLite so two process invocations cannot replay concurrently.
        with lock,db() as connection:
            claimed=connection.execute('UPDATE crm_pending SET next_attempt=? WHERE id=? AND next_attempt<=?',(int(time.time())+60,request_id,int(time.time()))).rowcount
        if not claimed:continue
        try:
            data=json.loads(body)
            files=[(f['name'],f['mime'],base64.b64decode(f['body'],validate=True)) for f in data['files']]
            send(data['payload'],files,data['result'])
        except Exception:
            with db() as connection:connection.execute('UPDATE crm_pending SET attempts=attempts+1,next_attempt=? WHERE id=?',(int(time.time())+min(3600,30*(2**min(attempts,7))),request_id))
            continue
        with db() as connection:
            connection.execute('UPDATE requests SET state=? WHERE id=?',('sent',request_id))
            connection.execute('DELETE FROM crm_pending WHERE id=?',(request_id,))
        sent+=1
    return sent
