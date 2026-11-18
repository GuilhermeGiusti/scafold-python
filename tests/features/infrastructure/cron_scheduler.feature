# language: pt
Funcionalidade: Agendador por cron do job da outbox

  Regra: um ciclo por disparo, nunca dois ao mesmo tempo

    Cenário: o primeiro ciclo espera o primeiro disparo, e não roda no boot
      Dado o relógio do agendador em "2026-11-18T12:00:30+00:00"
      Quando o agendador "* * * * *" roda 2 ciclos de 1 segundo
      Então os ciclos rodaram em "12:01:00, 12:02:00"

    Cenário: o disparo que cai durante um ciclo é pulado, com aviso
      Dado o relógio do agendador em "2026-11-18T12:00:30+00:00"
      Quando o agendador "* * * * *" roda 2 ciclos de 150 segundos
      Então os ciclos rodaram em "12:01:00, 12:04:00"
      E a cada ciclo o agendador avisou que pulou 2 disparos

  Regra: um ciclo que falha não derruba o agendador

    Cenário: depois de uma falha, o próximo disparo roda de novo
      Dado o relógio do agendador em "2026-11-18T12:00:30+00:00"
      E o primeiro ciclo falhando
      Quando o agendador "* * * * *" roda 2 ciclos de 1 segundo
      Então os ciclos rodaram em "12:01:00, 12:02:00"
      E o agendador registrou a falha do ciclo
