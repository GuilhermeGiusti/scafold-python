"""O que uma Strategy devolve: a união selada de três casos.

O retorno é uma união selada, e não um booleano: booleano não distingue "broker fora" de "destino
inexistente", e quem decide entre reagendar e matar precisa dessa diferença sem interpretar
exceção de broker, que é o conhecimento que a Strategy existe para conter.
"""

from __future__ import annotations

from scafold.domain.outbox.value_objects.permanent_failure import PermanentFailure
from scafold.domain.outbox.value_objects.published import Published
from scafold.domain.outbox.value_objects.transient_failure import TransientFailure

#: A união. Quem a trata usa `match` terminando em `case _: assert_never(...)`.
type DispatchOutcome = Published | TransientFailure | PermanentFailure
