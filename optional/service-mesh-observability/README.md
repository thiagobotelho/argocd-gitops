# Observabilidade opcional do mesh

```bash
oc apply -k optional/service-mesh-observability
oc -n openshift-gitops get application service-mesh
```

Este perfil substitui a fonte da mesma Application service-mesh por service-mesh-gitops/optional/observability. Requer Collector, Tempo, Prometheus Apps e Logging existentes. Mantém auto-sync/self-heal sem prune automático.

Consulte [componentes, pré-requisitos, logs, métricas, alertas e tracing](https://github.com/thiagobotelho/service-mesh-gitops/blob/main/docs/OBSERVABILIDADE.md). O perfil sem Kiali e o perfil somente com Kiali continuam disponíveis; não aplique dois perfis para a mesma Application.
