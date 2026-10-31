import unittest
import httpx
from local_pc.llm_probe import probe,validate_url

class LLMProbeTests(unittest.TestCase):
    def test_models_and_no_secret_or_inference(self):
        requests=[]
        def handler(request):
            requests.append(request)
            return httpx.Response(200,json={'data':[{'id':'local-model'},{'id':'vision-candidate'}]})
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result=probe('http://127.0.0.1:1234/v1',client)
        self.assertEqual(result['status'],'models_available');self.assertEqual(result['model_ids'],['local-model','vision-candidate'])
        self.assertEqual(str(requests[0].url),'http://127.0.0.1:1234/v1/models')
        self.assertEqual(requests[0].method,'GET');self.assertNotIn('authorization',requests[0].headers)
        self.assertFalse(result['vision_verified']);self.assertFalse(result['inference_tested'])
    def test_auth_redirect_large_and_invalid(self):
        for code,body,expected in [(401,{},'authentication_required'),(302,{},'redirect_refused'),(200,{'oops':1},'incompatible_response')]:
            with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(code,json=body))) as client:
                self.assertEqual(probe('http://localhost:1234/v1',client)['status'],expected)
        with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=b'x'*65537))) as client:
            self.assertEqual(probe('http://localhost:1234/v1',client)['status'],'response_too_large')
        for url in ['file:///tmp/x','http://user:pass@localhost:1234/v1','http://localhost/v1?token=secret','http://localhost/v1#x','http://localhost/other']:
            with self.assertRaises(ValueError):validate_url(url)
    def test_network_failure_is_not_invented_success(self):
        def handler(request):raise httpx.ConnectError('private error text',request=request)
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result=probe('http://localhost:11434/v1',client)
        self.assertEqual(result['status'],'unreachable');self.assertNotIn('private error',str(result))
