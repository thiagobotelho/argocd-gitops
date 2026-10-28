# Aplicações opcionais

```bash
oc apply -k optional
```

- Network Observability: perfil CRC com drops, DNS, RTT e métricas. O
  `Application` usa sync automático, mas só é criado quando este diretório
  opcional é aplicado.
- RHACS: tecnicamente possível, mas Central/Scanner adicionam pelo menos
  3 CPU e 6 GiB; instale apenas com memória disponível.
- RHACM: não recomendado para o laboratório de nó único. É uma plataforma de
  hub multicluster e seu custo não se justifica para gerenciar apenas o CRC.

- [Network Events experimental](network-events/README.md): opt-in separado, após
  habilitar e validar a FeatureGate manual. Não faz parte do comando acima.
