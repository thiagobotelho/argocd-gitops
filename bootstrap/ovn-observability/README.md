# OVNObservability opcional

Use somente em cluster descartável autorizado. Este bootstrap não participa
do App-of-Apps. TechPreviewNoUpgrade habilita um conjunto de recursos
experimentais, não apenas OVNObservability. Não há reversão suportada e
atualizações entre versões menores ficam impedidas.

## Habilitar o conjunto

```bash
oc whoami
oc whoami --show-server
oc get featuregate cluster -o yaml
oc get co
oc get mcp
oc kustomize bootstrap/ovn-observability
oc apply --dry-run=server -k bootstrap/ovn-observability
oc apply -k bootstrap/ovn-observability
```

Confira o ambiente antes do apply. A reconciliação pode reiniciar componentes
e afetar temporariamente a disponibilidade.

## Aguardar reconciliação

```bash
oc get featuregate cluster -o jsonpath='{.spec.featureSet}{"\n"}{range .status.featureGates[*]}{.version}{" "}{.enabled[?(@.name=="OVNObservability")].name}{"\n"}{end}'
oc get co
oc get mcp
oc -n openshift-ovn-kubernetes get pods
```

Confirme OVNObservability habilitado para a versão atual, Operators disponíveis
sem degradação/progressão e pools atualizados. A condição isolada Available
não basta enquanto a reconciliação estiver em andamento.

## Selecionar o perfil de coleta

Com MinIO, Loki e Network Observability preparados:

```bash
oc kustomize optional/network-events
oc apply -k optional/network-events
oc -n openshift-gitops get application network-observability
oc get flowcollector cluster -o jsonpath='{.spec.agent.ebpf.features}{"\n"}'
```

Isso mantém a mesma Application, apontando para o overlay
desenvolvimento-network-events do network-observability-gitops.

## Desativar somente a coleta experimental

```bash
oc apply -k optional
```

O perfil volta a desenvolvimento, sem NetworkEvents. Isso não reverte a
FeatureGate nem devolve elegibilidade a upgrades. Não use delete deste
bootstrap como mecanismo de reversão; para recuperar um cluster padrão,
planeje sua recriação e a restauração dos dados necessários.

Referência: [OpenShift 4.22: OVS sampling e OVNObservability](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/pdf/ovn-kubernetes_network_plugin/index).
