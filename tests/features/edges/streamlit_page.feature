# language: pt
Funcionalidade: Tela Streamlit de Examples

  A tela chama os mesmos use cases da API, pela mesma montagem. O cenário roda a tela de verdade,
  com o executor de testes do Streamlit, sobre os fakes.

  Regra: a tela cria e lista

    Cenário: sem Examples, a tela avisa que não há nenhum
      Quando abro a tela
      Então a tela mostra o aviso "Nenhum Example cadastrado."

    Cenário: criar mostra a confirmação e o Example na tabela
      Quando preencho o nome "Relatório" e os itens "Capa" e clico em criar
      Então a tela mostra a confirmação que começa com "Example criado:"
      E a tabela mostra o nome "Relatório" com 1 itens

  Regra: a recusa aparece na tela com o texto do presenter

    Cenário: nome repetido mostra o erro
      Dado a tela com o Example "Relatório" criado
      Quando preencho o nome "Relatório" e os itens "Capa" e clico em criar
      Então a tela mostra o erro "Já existe um Example com esse nome."
