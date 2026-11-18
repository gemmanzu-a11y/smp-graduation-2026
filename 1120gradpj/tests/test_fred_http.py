"""Credential parameter routing and response echo suppression without network access."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import smp_forecast.http as http

class Response(io.BytesIO):
    status=200

class FredHttpTest(unittest.TestCase):
    def test_each_service_uses_correct_auth_parameter_without_receipt_secret(self):
        for name,param in [('FRED_API_KEY','api_key'),('KPX_SERVICE_KEY','serviceKey'),('KMA_APIHUB_AUTH_KEY','authKey')]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                requests=[]
                def open_fake(request,**kwargs):
                    requests.append(request.full_url)
                    return Response(b'{"observations": []}')
                with patch.object(http,'ROOT',Path(d)),patch.object(http.urllib.request,'urlopen',open_fake):
                    payload,receipt=http.Client({name:'test-only'}).fetch('test','https://example.invalid/data',{'series_id':'DEMO'},name,refresh=True)
                    query=parse_qs(urlparse(requests[0]).query)
                    self.assertEqual(query[param],['test-only'])
                    self.assertNotIn(param,receipt['params'])
                    for f in Path(d).rglob('*'):
                        if f.is_file():self.assertNotIn(b'test-only',f.read_bytes())

    def test_echoed_key_is_not_saved(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(http,'ROOT',Path(d)),patch.object(http.urllib.request,'urlopen',lambda *a,**k:Response(b'test-only')):
                with self.assertRaises(http.FetchError):
                    http.Client({'FRED_API_KEY':'test-only'}).fetch('test','https://example.invalid/data',{},'FRED_API_KEY')
            self.assertFalse(list(Path(d).rglob('*.raw')))

if __name__=='__main__':unittest.main()
