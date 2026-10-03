import json
import httpx
import pytest
from backend.ollama_client import OllamaClient,OllamaError

def test_local_models_only_and_remote_alias_blocked():
    def handler(request):
        if request.url.path=='/api/tags':
            return httpx.Response(200,json={'models':[{'name':'llama3.2:3b'},{'name':'remote:cloud'},{'name':'alias','remote_host':'https://ollama.com'},{'name':'sneaky'}]})
        return httpx.Response(200,json={'remote_model':'a-remote-model'})
    client=OllamaClient(httpx.MockTransport(handler))
    assert client.list_models()==['llama3.2:3b','sneaky']
    with pytest.raises(OllamaError,match='remote service'): client.ensure_model('sneaky')
    with pytest.raises(OllamaError,match='ollama pull missing'): client.ensure_model('missing')

def test_chat_ignores_thinking_and_sends_schema():
    def handler(request):
        body=json.loads(request.content)
        assert request.url.host=='127.0.0.1' and body['stream'] is False
        assert len(body['format']['oneOf'])==7
        return httpx.Response(200,json={'message':{'content':'{"action":"final","answer":"Hello"}','thinking':'PRIVATE THOUGHT'}})
    assert 'PRIVATE' not in OllamaClient(httpx.MockTransport(handler)).chat('llama3.2:3b',[])

def test_connection_error():
    def handler(request): raise httpx.ConnectError('oops',request=request)
    with pytest.raises(OllamaError,match='ollama serve'): OllamaClient(httpx.MockTransport(handler)).list_models()


def test_malformed_message_is_helpful():
    client=OllamaClient(httpx.MockTransport(lambda request:httpx.Response(200,json={'message':None})))
    with pytest.raises(OllamaError,match='no answer'): client.chat('llama3.2:3b',[])
