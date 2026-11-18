"""Erro de domínio: o nome já pertence a outro Example."""


class LabelTaken(Exception):
    """Dois Examples não têm o mesmo nome.

    Quem garante a regra é o banco, pela restrição ``uq_example_label``, e não uma consulta
    anterior: duas criações simultâneas passariam as duas pela consulta. O repositório traduz a
    violação dessa restrição, pelo nome, neste erro.
    """
