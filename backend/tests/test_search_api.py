"""HTTP contract of the search endpoints, with a fake service (no models, no database)."""
import pytest
from fastapi.testclient import TestClient

from app.api.search import get_search_service
from app.main import app
from app.services.search import SearchError

PROVISION = {"role": "operative", "citation": "Article 17(1)", "article": 17, "article_title": "Right to erasure",
             "text": "The data subject shall have the right to obtain the erasure of personal data.", "score": 0.98,
             "chunk_id": "gdpr:art17:p1", "source_url": "https://eur-lex.europa.eu/x#017.001"}
RECITAL = {"role": "interpretive_context", "citation": "Recital 65", "text": "A data subject should have the right...",
           "score": 0.82, "relevance": 0.82, "chunk_id": "gdpr:rct65", "source_url": None}
SUPPORTED = {"question": "What is the right to be forgotten?", "status": "supported", "confidence": 0.984,
             "provisions": [PROVISION], "context": [RECITAL]}
NO_BASIS = {"question": "Tax in France?", "status": "no_basis", "confidence": 0.02, "note": "No GDPR provision supports an answer to this question.",
            "provisions": [], "context": []}


class FakeService:
    def __init__(self, state="ready", result=None, error=None):
        self.state, self.result, self.error, self.questions = state, result, error, []

    @property
    def ready(self):
        return self.state == "ready"

    async def search(self, question):
        self.questions.append(question)
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def client():
    with_service = {}

    def make(service):
        app.dependency_overrides[get_search_service] = lambda: service
        with_service["service"] = service
        return TestClient(app, raise_server_exceptions=False)

    yield make
    app.dependency_overrides.clear()


def post(c, body):
    return c.post("/api/search", json=body)


def test_supported_answer_has_the_documented_shape(client):
    svc = FakeService(result=SUPPORTED)
    r = post(client(svc), {"question": "What is the right to be forgotten?"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "supported" and body["provisions"][0]["citation"] == "Article 17(1)"
    assert body["context"][0]["role"] == "interpretive_context"
    assert isinstance(body["took_ms"], int) and body["note"] is None


def test_no_basis_returns_empty_lists_not_an_error(client):
    r = post(client(FakeService(result=NO_BASIS)), {"question": "Tax in France?"})
    assert r.status_code == 200
    assert r.json()["status"] == "no_basis" and r.json()["provisions"] == [] and r.json()["context"] == []


def test_question_is_trimmed_before_it_reaches_the_service(client):
    svc = FakeService(result=SUPPORTED)
    assert post(client(svc), {"question": "   right to be forgotten?  "}).status_code == 200
    assert svc.questions == ["right to be forgotten?"]


@pytest.mark.parametrize("body", [{"question": ""}, {"question": "   \n\t "}, {}, {"question": 5}, {"question": "x" * 501}, {"q": "hi"}])
def test_invalid_input_is_rejected_with_422_and_never_reaches_the_service(client, body):
    svc = FakeService(result=SUPPORTED)
    assert post(client(svc), body).status_code == 422
    assert svc.questions == []


def test_a_question_of_exactly_the_maximum_length_is_accepted(client):
    assert post(client(FakeService(result=SUPPORTED)), {"question": "x" * 500}).status_code == 200


@pytest.mark.parametrize("error,status,code,retry", [
    (SearchError("search_loading", "starting up", 503, retry_after=5), 503, "search_loading", "5"),
    (SearchError("search_unavailable", "not available", 503), 503, "search_unavailable", None),
    (SearchError("search_busy", "busy", 429, retry_after=5), 429, "search_busy", "5"),
    (SearchError("search_timeout", "too slow", 504), 504, "search_timeout", None),
])
def test_known_failures_map_to_status_codes_with_structured_errors(client, error, status, code, retry):
    r = post(client(FakeService(error=error)), {"question": "anything"})
    assert r.status_code == status
    assert r.json()["detail"] == {"code": code, "message": error.message}
    assert r.headers.get("retry-after") == retry


def test_unexpected_failures_do_not_leak_internals(client):
    r = post(client(FakeService(error=RuntimeError("secret connection string postgres://user:pw@host"))), {"question": "anything"})
    assert r.status_code == 500
    assert r.json()["detail"] == {"code": "search_failed", "message": "The search could not be completed. Please try again."}
    assert "secret" not in r.text and "postgres" not in r.text and "Traceback" not in r.text


def test_malformed_pipeline_output_is_a_500_not_a_crash(client):
    r = post(client(FakeService(result={"question": "q", "status": "maybe"})), {"question": "anything"})
    assert r.status_code == 500 and "maybe" not in r.text


@pytest.mark.parametrize("state,ready", [("loading", False), ("ready", True), ("unavailable", False), ("failed", False)])
def test_status_endpoint_reports_the_engine_state(client, state, ready):
    r = client(FakeService(state=state)).get("/api/search/status")
    assert r.status_code == 200 and r.json() == {"state": state, "ready": ready}


def test_existing_routes_are_unchanged(client):
    c = client(FakeService())
    assert c.get("/").json() == {"service": "Regulatory & Compliance Intelligence Hub", "status": "online"}
    paths = {r.path for r in app.routes}
    assert {"/api/health", "/api/search", "/api/search/status"} <= paths
