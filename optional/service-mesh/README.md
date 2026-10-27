# Service Mesh no Argo CD

A Application `service-mesh` gerencia o Operator, os namespaces de infraestrutura, IstioCNI, Istio, a tag de revisão e os monitores. A fonte é `service-mesh-gitops/overlays/desenvolvimento`. As APIs e políticas dos exercícios permanecem manuais no repositório `mesh-apps-lab`.

## Instalação

Configure previamente as verificações de saúde Sail entregues por `base/argocd.yaml` e instale as CRDs do monitoramento. Confira compatibilidade do catálogo e capacidade do cluster antes de cadastrar:

```bash
oc apply -k optional/service-mesh
```

Sincronize `service-mesh` pelo Argo CD. As waves ordenam namespaces, Subscription, CNI, Istio, tag e monitores. A saúde da Subscription deve permanecer Progressing enquanto a instalação inicial aguarda aprovação. Inspecione e aprove somente o InstallPlan da versão escolhida; aguarde CSV Succeeded e CRDs Established. `SkipDryRunOnMissingResource` evita falha de dry-run das CRDs Sail ainda ausentes e não substitui a instalação do Operator.

A sincronização é manual e a Application não possui finalizer de exclusão em cascata. Consulte os guias de instalação e operação do repositório `service-mesh-gitops`.

## Migrar de Applications separadas

1. Confira que `service-mesh-operator`, `service-mesh-control-plane` e `service-mesh-monitoring` não têm operações em andamento, sincronização automática ou finalizers. Salve seus manifests e inventário dos recursos.
2. Retire somente esses três objetos Application sem cascata. Não exclua os manifests de infraestrutura com `oc delete -k` e não remova finalizers sem revisar sua finalidade.
3. Cadastre `service-mesh`, confira o diff e sincronize inicialmente sem prune. Os recursos existentes são reconciliados com a nova identificação de propriedade, sem reinstalar o Operator ou recriar namespaces.
4. Confirme Synced/Healthy, a revisão ativa, CNI, tag, monitores e preservação das APIs. Não mantenha duas Applications gerenciando os mesmos recursos.

Para reverter a migração, retire `service-mesh` sem cascata e recadastre as três definições anteriores a partir da revisão Git salva. Confira propriedade e diff antes de sincronizar, sem prune.
