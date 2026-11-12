import json
import unittest
from unittest.mock import patch
from io import BytesIO
from fastapi import HTTPException
from app import ai
from app.main import OBJECTS, Compose, compose


class AITests(unittest.TestCase):
    def setUp(self):
        ai.calls.clear()
        ai.cache.clear()

    def response(self, items):
        content=json.dumps({'items':items,'explanation':'Книга — знания, монета — инвестиции.'})
        return BytesIO(json.dumps({'choices':[{'message':{'content':content}}]}).encode())

    @patch('app.ai.settings', return_value={'GROQ_API_KEY':'test-only','GROQ_MODEL':'test'})
    def test_selection_is_validated_and_cached(self, settings):
        with patch('app.ai.urlopen', return_value=self.response([
            {'id':'book','role':'main'},{'id':'coin','role':'background'}])) as network:
            result=compose(Compose(idea='Инвестиции в знания'))
            self.assertEqual(result['scene']['items'][0]['role'],'background')
            self.assertEqual(result['scene']['items'][-1]['id'],'book')
            self.assertNotIn('test-only',json.dumps(result))
            ai.select_objects('Инвестиции в знания',OBJECTS)
            self.assertEqual(network.call_count,1)

    @patch('app.ai.settings', return_value={'GROQ_API_KEY':'test-only','GROQ_MODEL':'test'})
    def test_invented_object_rejected(self, settings):
        with patch('app.ai.urlopen', return_value=self.response([{'id':'dragon','role':'main'}])):
            with self.assertRaises(HTTPException) as result:
                ai.select_objects('Тема',OBJECTS)
            self.assertEqual(result.exception.status_code,502)

    @patch('app.ai.settings', return_value={'GROQ_API_KEY':'','GROQ_MODEL':'test'})
    def test_missing_key_makes_no_request(self, settings):
        with patch('app.ai.urlopen') as network:
            with self.assertRaises(HTTPException):
                ai.select_objects('Тема',OBJECTS)
            network.assert_not_called()
