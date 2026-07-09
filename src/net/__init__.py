"""Camada de transporte de rede.

Os atores da simulação são processos distribuídos reais que se comunicam via
HTTP, rodando como containers Docker separados em uma rede compartilhada. Esta
camada é apenas o transporte: o significado vive nas camadas internas
(``domain``, ``generation``, ``standardization``, ``metrics``) e no núcleo do
banco de dados (``src/database.py``).
"""
