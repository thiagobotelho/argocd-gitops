# Service Mesh no Argo CD

O AppProject `service-mesh` limita fonte, destinos e tipos de recurso. A Application `service-mesh` gerencia o Operator, os namespaces de infraestrutura, IstioCNI, Istio, a tag de revisão e os monitores. A fonte é `service-mesh-gitops/overlays/desenvolvimento`. As APIs e políticas dos exercícios permanecem manuais no repositório `mesh-apps-lab`.

## Instalação

Configure previamente as verificações de saúde Sail entregues por `base/argocd.yaml` e instale as CRDs do monitoramento. Confira compatibilidade do catálogo e capacidade do cluster antes de cadastrar:

```bash
oc apply -k optional/service-mesh
```

A Application inicia a sincronização automaticamente. As waves ordenam namespaces, Subscription, CNI, Istio, tag e monitores. A Subscription aprova automaticamente a instalação e as atualizações no canal `stable-3.4`. Aguarde CSV Succeeded e CRDs Established. `SkipDryRunOnMissingResource` evita falha de dry-run das CRDs Sail ainda ausentes e não substitui a instalação do Operator.

O auto-sync aplica mudanças da branch `main` e o self-heal corrige divergências no cluster. O prune permanece desativado e a Application não possui finalizer de exclusão em cascata. `startingCSV` define a versão inicial, sem fixar atualizações futuras. Para exigir revisão de cada atualização do operador, altere `installPlanApproval` para `Manual` no repositório `service-mesh-gitops`. Consulte os guias de instalação e operação do repositório `service-mesh-gitops`.

## Migrar de Applications separadas

Antes de migrar recursos existentes, desative temporariamente `spec.syncPolicy.automated` no manifesto da nova Application para revisar a adoção. Reative após conferir a propriedade.

1. Confira que `service-mesh-operator`, `service-mesh-control-plane` e `service-mesh-monitoring` não têm operações em andamento, sincronização automática ou finalizers. Salve seus manifests e inventário dos recursos.
2. Retire somente esses três objetos Application sem cascata. Não exclua os manifests de infraestrutura com `oc delete -k` e não remova finalizers sem revisar sua finalidade.
3. Cadastre `service-mesh`, confira o diff e sincronize inicialmente sem prune. Os recursos existentes são reconciliados com a nova identificação de propriedade, sem reinstalar o Operator ou recriar namespaces.
4. Confirme Synced/Healthy, a revisão ativa, CNI, tag, monitores e preservação das APIs. Não mantenha duas Applications gerenciando os mesmos recursos.

Para reverter a migração, retire `service-mesh` sem cascata e recadastre as três definições anteriores a partir da revisão Git salva. Confira propriedade e diff antes de sincronizar, sem prune.
