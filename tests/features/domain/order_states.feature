# language: pt
@domain
Funcionalidade: Pedido com um tipo por estado

  Cada estado do pedido é um tipo, e a transição é um método do estado de origem que devolve o
  estado de destino. A transição proibida, como cancelar um pedido enviado, não tem método: quem a
  recusa é o mypy, antes de o código rodar. Estes cenários provam o que vale em runtime.

  Regra: a transição devolve o estado de destino e não muda o de origem

    Cenário: pedido pago e enviado chega ao estado enviado com o código de rastreio
      Dado um pedido feito com 2 unidades de "SKU-1" a 10.00
      Quando o pagamento é aprovado e o pedido é enviado com o código "BR123456789XX"
      Então o pedido está "enviado: BR123456789XX"
      E o pedido feito continua "aguardando pagamento"
      E o total do pedido é 20.00

    Cenário: pagamento recusado cancela o pedido com o motivo
      Dado um pedido feito com 1 unidades de "SKU-1" a 10.00
      Quando o pagamento é recusado por "cartão negado"
      Então o pedido está "cancelado: cartão negado"

  Regra: um estado só existe válido

    Cenário: pedido sem itens é recusado
      Quando faço um pedido sem itens
      Então a operação é recusada por pedido vazio

    Cenário: item com quantidade zero é recusado
      Quando faço um pedido com 0 unidades de "SKU-1" a 10.00
      Então a operação é recusada por quantidade inválida

    Esquema do Cenário: código de rastreio fora do formato não cria o pedido enviado
      Dado um pedido feito com 1 unidades de "SKU-1" a 10.00
      Quando o pagamento é aprovado e o pedido é enviado com o código "<código>"
      Então a operação é recusada por código de rastreio inválido

      Exemplos:
        | código         |
        | BR123          |
        | br123456789xx  |
