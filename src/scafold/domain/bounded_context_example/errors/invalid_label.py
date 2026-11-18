"""Erro de domínio: o nome do Example não cumpre a regra."""


class InvalidLabel(Exception):
    """O nome do Example, sem os espaços das pontas, precisa ter de 1 a 64 caracteres."""
