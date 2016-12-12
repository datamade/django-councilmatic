from django.test import TestCase, Client

from councilmatic_core.models import Organization, Bill, Person, Event


class RouteTest(TestCase):
    fixtures = [
        'organization.json',
        'membership.json',
        'bill.json',
        'person.json',
        'post.json',
        'event.json',
    ]

    def getPage(self, url):
        client = Client()
        return client.get(url)

    def test_index(self):
        assert self.getPage('/').status_code == 200

    def test_about(self):
        assert self.getPage('/about/').status_code == 200

    def test_committees(self):
        assert self.getPage('/committees/').status_code == 200

    def test_council_members(self):
        assert self.getPage('/council-members/').status_code == 200

    def test_committee(self):
        for committee in Organization.committees():
            committee_url = '/committee/{}/'.format(committee.slug)
            assert self.getPage(committee_url).status_code == 200

    def test_committee_event_rss(self):
        for committee in Organization.committees():
            committee_url = '/committee/{}/events/rss/'.format(committee.slug)
            assert self.getPage(committee_url).status_code == 200

    def test_committee_action_rss(self):
        for committee in Organization.committees():
            committee_url = '/committee/{}/actions/rss/'.format(committee.slug)
            assert self.getPage(committee_url).status_code == 200

    def test_committee_widget(self):
        for committee in Organization.committees():
            committee_url = '/committee/{}/widget/'.format(committee.slug)
            assert self.getPage(committee_url).status_code == 200

    def test_bill(self):
        for bill in Bill.objects.all():
            url = '/legislation/{}/'.format(bill.slug)
            assert self.getPage(url).status_code == 200

    def test_bill_rss(self):
        for bill in Bill.objects.all():
            url = '/legislation/{}/rss/'.format(bill.slug)
            assert self.getPage(url).status_code == 200

    def test_bill_widget(self):
        for bill in Bill.objects.all():
            url = '/legislation/{}/widget/'.format(bill.slug)
            assert self.getPage(url).status_code == 200

    def test_person(self):
        for person in Person.objects.all():
            url = '/person/{}/'.format(person.slug)
            assert self.getPage(url).status_code == 200

    def test_person_rss(self):
        for person in Person.objects.all():
            url = '/person/{}/rss/'.format(person.slug)
            assert self.getPage(url).status_code == 200

    def test_person_widget(self):
        for person in Person.objects.all():
            url = '/person/{}/widget/'.format(person.slug)
            assert self.getPage(url).status_code == 200

    def test_events(self):
        assert self.getPage('/events/').status_code == 200

    def test_event(self):
        for event in Event.objects.all():
            url = '/event/{}/'.format(event.slug)
            assert self.getPage(url).status_code == 200
