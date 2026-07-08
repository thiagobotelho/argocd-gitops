# Aplicações opcionais

```bash
oc apply -k optional
```

- Network Observability: viável no CRC com amostragem alta e métricas. O
  `Application` usa sync automático, mas só é criado quando este diretório
  opcional é aplicado.
- RHACS: tecnicamente possível, mas Central/Scanner adicionam pelo menos
  3 CPU e 6 GiB; instale apenas com memória disponível.
- RHACM: não recomendado para o laboratório de nó único. É uma plataforma de
  hub multicluster e seu custo não se justifica para gerenciar apenas o CRC.
