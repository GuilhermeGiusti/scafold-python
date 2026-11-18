# language: pt
Funcionalidade: Portões do schema e do acesso SQL-first

  Cada regra é provada duas vezes: contra os arquivos reais, onde não acha nada, e contra um
  exemplo errado, onde acha. Um portão que nunca reprova nada não prova nada.

  Regra: o acesso é SQL-first, e o ORM do SQLAlchemy não entra

    Cenário: nenhum módulo de src e de tests importa o ORM
      Quando procuro imports do ORM no projeto
      Então nada é encontrado

    Cenário: o portão reprova import do ORM e aceita o Core
      Quando procuro imports do ORM no código "from sqlalchemy.orm import Session\nfrom sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession"
      Então são encontrados "sqlalchemy.orm, sqlalchemy.ext.asyncio.AsyncSession"

  Regra: o schema só recusa, e toda restrição tem nome com o prefixo do tipo

    Esquema do Cenário: as migrations do projeto cumprem a regra
      Quando aplico a regra "<regra>" às migrations do projeto
      Então nada é encontrado

      Exemplos:
        | regra                          |
        | objetos que fazem o banco agir |
        | DEFAULT de instante            |
        | restrições sem nome            |

    Esquema do Cenário: a regra reprova o exemplo errado
      Quando aplico a regra "<regra>" ao SQL "<sql>"
      Então a regra encontra uma violação

      Exemplos:
        | regra                          | sql                                                      |
        | objetos que fazem o banco agir | CREATE TRIGGER t BEFORE INSERT ON x FOR EACH ROW EXECUTE |
        | DEFAULT de instante            | CREATE TABLE x (at timestamptz DEFAULT now())            |
        | restrições sem nome            | CREATE TABLE x (id uuid PRIMARY KEY)                     |
