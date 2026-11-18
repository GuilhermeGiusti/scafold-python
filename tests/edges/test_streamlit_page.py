import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from streamlit.testing.v1 import AppTest

scenarios("edges/streamlit_page.feature")

#: A primeira execução importa o projeto inteiro; o padrão de 3 s do executor é curto.
TIMEOUT_SECONDS = 30


def page_over_fakes() -> None:
    """O script que o executor roda. Ele é copiado como texto: os imports ficam aqui dentro."""
    from tests.support.streamlit_scene import render_over_fakes

    render_over_fakes()


@pytest.fixture
def screen() -> AppTest:
    app = AppTest.from_function(page_over_fakes, default_timeout=TIMEOUT_SECONDS)
    app.run()
    return app


def submit(screen: AppTest, label: str, items: str) -> None:
    screen.text_input(key="label").input(label)
    screen.text_area(key="items").input(items)
    screen.button(key="create").click()
    screen.run()


@given(parsers.parse('a tela com o Example "{label}" criado'))
def _(screen: AppTest, label: str) -> None:
    submit(screen, label, "")
    assert not screen.exception


@when("abro a tela")
def _(screen: AppTest) -> None:
    assert not screen.exception


@when(parsers.parse('preencho o nome "{label}" e os itens "{items}" e clico em criar'))
def _(screen: AppTest, label: str, items: str) -> None:
    submit(screen, label, items)
    assert not screen.exception


@then(parsers.parse('a tela mostra o aviso "{text}"'))
def _(screen: AppTest, text: str) -> None:
    assert [info.value for info in screen.info] == [text]


@then(parsers.parse('a tela mostra a confirmação que começa com "{text}"'))
def _(screen: AppTest, text: str) -> None:
    [success] = screen.success
    assert str(success.value).startswith(text)


@then(parsers.parse('a tela mostra o erro "{text}"'))
def _(screen: AppTest, text: str) -> None:
    assert [error.value for error in screen.error] == [text]


@then(parsers.parse('a tabela mostra o nome "{label}" com {count:d} itens'))
def _(screen: AppTest, label: str, count: int) -> None:
    [table] = screen.dataframe
    rows = table.value.to_dict("records")
    assert [(row["Nome"], row["Itens"]) for row in rows] == [(label, count)]
