# Network Events opcional

Pré-requisito obrigatório: executar e validar o
[bootstrap OVNObservability](../../bootstrap/ovn-observability/README.md).

```bash
oc apply -k optional/network-events
```

Reutiliza a Application network-observability. Altera somente o caminho de
origem para overlays/desenvolvimento-network-events. Não habilita FeatureGate,
não cria outro LokiStack nem outro FlowCollector.

O diretório optional padrão continua selecionando desenvolvimento, sem
NetworkEvents. Aplicá-lo novamente desativa a coleta experimental, mas não
reverte TechPreviewNoUpgrade.

No Console: Observe → Network Traffic → visão Network Events. Gere tráfego
novo e confira os eventos de permissão/descarte e seus metadados.
