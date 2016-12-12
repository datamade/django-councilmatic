from django.test import TestCase, Client
from django.db import connection


class RouteTest(TestCase):
    fixtures = ['bill.json']

    def test_index(self):
        client = Client()
        response = client.get('/')
        assert response.status_code == 200
