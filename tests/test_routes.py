from django.core.management import call_command
import pytest

from councilmatic_core.models import Organization, Bill, Person, Event


@pytest.fixture(scope="module")
def route_setup(django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "tests/fixtures/test_data.json")

    yield

    django_db_blocker.restore()


@pytest.mark.parametrize("councilmatic_url", ["/", "/about/"])
@pytest.mark.django_db
def test_routes_without_data(client, councilmatic_url):
    rv = client.get(councilmatic_url)
    assert rv.status_code == 200


@pytest.mark.django_db
def test_committee_routes(route_setup, client):
    assert client.get("/committees/").status_code == 200

    for committee in Organization.objects.all():
        committee_url = "/committee/{}/".format(committee.slug)
        assert client.get(committee_url).status_code == 200

        rss_events_url = "/committee/{}/events/rss/".format(committee.slug)
        assert client.get(rss_events_url).status_code == 200

        rss_actions_url = "/committee/{}/actions/rss/".format(committee.slug)
        assert client.get(rss_actions_url).status_code == 200

        widget_url = "/committee/{}/widget/".format(committee.slug)
        assert client.get(widget_url).status_code == 200


@pytest.mark.django_db
def test_bill_routes(route_setup, client):
    for bill in Bill.objects.all():
        bill_url = "/legislation/{}/".format(bill.slug)
        assert client.get(bill_url).status_code == 200

        rss_url = "/legislation/{}/rss/".format(bill.slug)
        assert client.get(rss_url).status_code == 200

        widget_url = "/legislation/{}/widget/".format(bill.slug)
        assert client.get(widget_url).status_code == 200


@pytest.mark.django_db
def test_person_routes(route_setup, client):
    for person in Person.objects.all():
        person_url = "/person/{}/".format(person.slug)
        assert client.get(person_url).status_code == 200

        rss_url = "/person/{}/rss/".format(person.slug)
        assert client.get(rss_url).status_code == 200

        widget_url = "/person/{}/widget/".format(person.slug)
        assert client.get(widget_url).status_code == 200


@pytest.mark.django_db
def test_person_routes(route_setup, client):
    assert client.get("/events/").status_code == 200

    for event in Event.objects.all():
        event_url = "/event/{}/".format(event.slug)
        assert client.get(event_url).status_code == 200
