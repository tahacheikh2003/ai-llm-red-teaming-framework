"""Ollama HTTP client. Only loopback inference and installed local models."""
import json
import httpx

DEFAULT_MODEL = 'llama3.2:3b'
OLLAMA_URL = 'http://127.0.0.1:11434'
from security.tool_policy import ARGUMENT_MODELS

# The grammar gives each tool its own argument schema, not a bag of mixed fields.
ACTION_SCHEMA = {
    'oneOf': [
        {'type':'object','properties':{
            'action':{'const':'tool'}, 'tool':{'const':name},
            'arguments':argument_model.model_json_schema()},
         'required':['action','tool','arguments'],'additionalProperties':False}
        for name,argument_model in ARGUMENT_MODELS.items()
    ] + [
        {'type':'object','properties':{'action':{'const':'final'},'answer':{'type':'string'}},
         'required':['action','answer'],'additionalProperties':False}
    ]
}

class OllamaError(RuntimeError):
    pass

def remote_model(item):
    name = item.get('name',item.get('model','')).lower()
    return bool(item.get('remote_host') or item.get('remote_model') or 'cloud' in name)

class OllamaClient:
    def __init__(self, transport=None):
        self.transport = transport

    def _request(self, method, path, payload=None, timeout=8):
        try:
            with httpx.Client(base_url=OLLAMA_URL,trust_env=False,transport=self.transport,timeout=httpx.Timeout(timeout,connect=3),follow_redirects=False) as client:
                result = client.request(method,path,json=payload)
                if result.status_code >= 300:
                    # Never return arbitrary upstream text, prompts, or model output in errors.
                    raise OllamaError(f'Ollama returned HTTP {result.status_code}. Check the model with ollama list, then retry or select another installed local model.')
                value = result.json()
                if not isinstance(value,dict) or value.get('error'):
                    raise OllamaError('Ollama returned an invalid response. Check the Ollama server and retry.')
                return value
        except httpx.TimeoutException as exc:
            raise OllamaError('Ollama timed out. Close memory-heavy apps, warm the model with ollama run llama3.2:3b, then retry.') from exc
        except httpx.RequestError as exc:
            raise OllamaError('Cannot reach Ollama. Open Ollama from the Start menu or run ollama serve. If it is not installed, install Ollama for Windows first.') from exc
        except ValueError as exc:
            raise OllamaError('Ollama returned malformed JSON. Restart Ollama and retry.') from exc

    def list_models(self):
        data = self._request('GET','/api/tags')
        models = data.get('models')
        if not isinstance(models,list):
            raise OllamaError('Ollama model list is malformed. Restart Ollama.')
        return sorted({m['name'] for m in models if isinstance(m,dict) and isinstance(m.get('name'),str) and not remote_model(m)})

    def ensure_model(self, model):
        if 'cloud' in model.lower():
            raise OllamaError('Cloud models are disabled. Select an installed local model.')
        if model not in self.list_models():
            raise OllamaError(f'Selected model is not installed locally. Run: ollama pull {model}')
        info = self._request('POST','/api/show',{'model':model})
        if remote_model(info):
            raise OllamaError('This model points to a remote service. Select an installed local model.')
        return info

    def chat(self, model, messages):
        payload={'model':model,'messages':messages,'stream':False,'format':ACTION_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':512},'keep_alive':'10m'}
        data = self._request('POST','/api/chat',payload,timeout=180)
        # message.thinking, timings, and raw envelopes are intentionally discarded.
        message = data.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        if not isinstance(content,str) or not content.strip():
            raise OllamaError('Ollama returned no answer. Try another installed local model.')
        return content
