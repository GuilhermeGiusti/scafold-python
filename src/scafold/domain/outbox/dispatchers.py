"""Os dispatchers que a outbox conhece e o limite de tentativas de uma mensagem.

O carimbo é gravado na linha no momento da gravação e decide por qual Strategy ela sai: a linha
nunca sai por outra (ADR-006). O banco recusa qualquer outro carimbo pela restrição
``ck_outbox_message_dispatcher``.

Uma Strategy nova entra aqui, junto com a migration que acrescenta o carimbo ao ``CHECK`` e a
tabela de dados de envio dela, e com a classe que cumpre ``IDispatcher``.
"""

from __future__ import annotations

#: O carimbo das mensagens entregues ao RabbitMQ.
RABBITMQ_DISPATCHER = "rabbitmq"

#: Os carimbos aceitos pelo gravador e semeados com zero no backlog.
KNOWN_DISPATCHERS: tuple[str, ...] = (RABBITMQ_DISPATCHER,)

#: Quantas falhas uma mensagem acumula antes de morrer. Constante, sem variável de ambiente
#: (ADR-006): cinco tentativas com a espera padrão de 30 s dão cerca de 2,5 minutos de tolerância.
MAX_ATTEMPTS = 5
