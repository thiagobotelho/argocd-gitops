# ACM e múltiplos clusters

Este diretório é opcional e não faz parte do fluxo CRC local. Ele prepara o
repositório para um hub Red Hat Advanced Cluster Management com OpenShift GitOps
gerenciando três clusters/ambientes.

## Por que usar ApplicationSet

No CRC local, os `Application` têm nomes simples como `grafana`, `zabbix` e
`keycloak-dev`. Em um Argo CD central no ACM, esses nomes colidem quando a
mesma aplicação é criada para mais de um cluster.

O `ApplicationSet` deste diretório gera nomes no formato:

```text
<cluster-normalizado>-<ambiente>-<componente>
```

Exemplo:

```text
crc-dev-desenvolvimento-grafana
ocp-aceite-aceite-grafana
ocp-prd-producao-grafana
```

O campo `nameNormalized` do Argo CD transforma nomes de clusters em nomes válidos
para recursos Kubernetes.

## Labels obrigatórios

Os clusters/Secrets registrados no Argo CD precisam ter:

| Label | Exemplo | Uso |
|---|---|---|
| `gitops.stack/managed` | `true` | seleciona clusters da stack |
| `gitops.stack/environment` | `desenvolvimento`, `aceite` ou `producao` | escolhe o overlay |
| `gitops.stack/keycloak-namespace` | `keycloak-dev`, `keycloak-aceite`, `keycloak-producao` | namespace de destino do Keycloak |

Exemplo no ACM:

```bash
oc label managedcluster crc-dev \
  gitops.stack/managed=true \
  gitops.stack/environment=desenvolvimento \
  gitops.stack/keycloak-namespace=keycloak-dev
```

Se o `GitOpsCluster` não propagar labels customizados para os Secrets de cluster
do Argo CD, aplique os mesmos labels nos Secrets em `openshift-gitops`:

```bash
oc -n openshift-gitops label secret <cluster-secret> \
  gitops.stack/managed=true \
  gitops.stack/environment=desenvolvimento \
  gitops.stack/keycloak-namespace=keycloak-dev
```

## Aplicação

Pré-requisitos:

- ACM instalado no hub;
- OpenShift GitOps instalado no hub;
- clusters importados no ACM;
- `ManagedClusterSetBinding` criado para o namespace `openshift-gitops`;
- labels acima aplicados nos clusters e/ou Secrets do Argo CD.

Aplicar:

```bash
oc apply -k optional/acm
```

Validar:

```bash
oc -n openshift-gitops get placement,gitopscluster,applicationset
oc -n openshift-gitops get applications -l app.kubernetes.io/part-of=openshift-local-stack
```

## Modelo de operação

- O CRC local continua usando `overlays/desenvolvimento/platform-apps.yaml`.
- O ACM deve usar `optional/acm/applicationset-platform.yaml`.
- Todos os Applications gerados têm sync automático com `prune` e `selfHeal`.
- A escolha do overlay vem do label `gitops.stack/environment`, não do nome do
  cluster. Assim um cluster pode se chamar `spoke-01` e ainda apontar para
  `producao` de forma explícita.

## Limitações

- Este diretório é um ponto de partida seguro; valide RBAC, quotas e políticas
  por ambiente antes de produção.
- O `ApplicationSet` assume branch `main` nos repositórios de cada componente.
- Componentes opcionais, como Network Observability, continuam fora do
  ApplicationSet principal.
