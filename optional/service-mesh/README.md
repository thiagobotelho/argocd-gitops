# Infraestrutura opcional de Service Mesh

Este módulo cadastra três Applications com sincronização manual:

- service-mesh-operator: Subscription do Operator.
- service-mesh-control-plane: Istio, IstioCNI, tag e namespaces de infraestrutura.
- service-mesh-monitoring: monitores para o Prometheus existente.

```bash
oc apply -k optional/service-mesh
```

Sincronize o Operator, revise e aprove o InstallPlan específico, aguarde CSV/CRDs, depois sincronize o plano de controle. Instale o monitoramento após conferir namespaces e seletores. Sync waves entre Applications independentes não substituem esses pré-requisitos.

As APIs e políticas dos exercícios não são gerenciadas por este módulo. Use o repositório [mesh-apps-lab](https://github.com/thiagobotelho/mesh-apps-lab) manualmente. Nenhuma Application deve apontar para seus cenários.

Tracing: optional/tracing substitui a fonte do mesmo Application de plano de controle; não crie dois proprietários do Istio. Consulte o [guia de instalação](https://github.com/thiagobotelho/service-mesh-gitops/blob/main/docs/INSTALACAO-CRC.md).
