# Tutorial CRC/OpenShift Local da stack GitOps

Este roteiro aplica a stack local a partir dos repositórios GitHub da solução.
Ele não depende de um caminho local fixo: escolha um diretório de trabalho,
clone os repositórios e execute os comandos a partir dele.

## 1. O que será instalado

| Recurso | Para que serve |
|---|---|
| OpenShift GitOps/Argo CD | Controla os repositórios GitOps, faz sync automático, prune e self-heal. |
| MetalLB | Fornece IPs `LoadBalancer` no CRC quando necessário. |
| Prometheus Apps | Coleta métricas de aplicações com exemplares e customizações fora do Prometheus nativo da plataforma. |
| Pyroscope | Armazena profiles para Profiles Drilldown e futura correlação trace → profile. |
| Loki | Recebe logs do OpenShift e permite correlação logs ↔ traces no Grafana. |
| Tempo | Armazena traces OTLP em modo leve `TempoMonolithic` para o CRC. |
| OpenTelemetry Collector | Recebe OTLP das aplicações, envia traces ao Tempo e expõe métricas RED. |
| Keycloak | Realm central `observability`, usuários, grupos, client OIDC do Grafana e client SAML do Zabbix. |
| Grafana | Dashboards, datasources Prometheus/Loki/Tempo/Zabbix, autenticação via Keycloak e drilldown. |
| Zabbix | Monitoramento sintético/API e integração com Grafana. |
| Network Observability | Opcional; coleta fluxos de rede com eBPF e políticas do FlowCollector. |

## 2. Clonar os repositórios

Defina a URL base pública onde os repositórios estão publicados e um diretório
de trabalho local qualquer. Use HTTPS ou SSH conforme seu ambiente. O exemplo
usa placeholder; substitua por sua organização, fork ou mirror.

```bash
export GIT_BASE_URL="https://github.com/thiagobotelho"
export WORKDIR="${PWD}/openshift-local-stack"

mkdir -p "${WORKDIR}"
cd "${WORKDIR}"

for repo in \
  openshift-local-installer \
  argocd-gitops \
  metallb-gitops \
  prometheus-gitops \
  pyroscope-gitops \
  loki-gitops \
  tempo-gitops \
  opentelemetry-gitops \
  keycloak-gitops \
  grafana-gitops \
  zabbix-gitops \
  network-observability-gitops
do
  if [ -d "${repo}/.git" ]; then
    git -C "${repo}" pull --ff-only
  else
    git clone "${GIT_BASE_URL}/${repo}.git"
  fi
done
```

Se você fez fork dos repositórios, altere `GIT_BASE_URL` para o fork antes de
executar o loop e revise os `repoURL` das `Application` no `argocd-gitops`.

## 3. Preparar o CRC

Use recursos altos o bastante para a stack de observabilidade:

```bash
crc config set enable-cluster-monitoring true
crc config set cpus 8
crc config set memory 32768
crc stop
crc start
```

Autentique o `oc`:

```bash
eval "$(crc oc-env)"
oc login -u kubeadmin https://api.crc.testing:6443
oc whoami
```

Valide o cluster:

```bash
cd "${WORKDIR}/openshift-local-installer"
cp -n .env.example .env
scripts/validate-crc.sh
```

Se `crc` ou `oc` não estiverem no `PATH`, o validador tenta usar binários
conhecidos, como `bin/crc-linux-*/crc`, `~/.local/bin/oc` ou o cache do CRC. Se
necessário, edite `.env` e defina caminhos locais:

```dotenv
CRC_BIN=/caminho/para/crc
OC_BIN=/caminho/para/oc
```

Avisos de namespace ausente são esperados antes do app-of-apps subir.

## 4. Criar os Secrets obrigatórios

Nenhuma senha real deve ser commitada. Os comandos abaixo são idempotentes
porque usam `--dry-run=client -o yaml | oc apply -f -`.

### 4.1 Loki/MinIO

```bash
export MINIO_ROOT_USER=minio
export MINIO_ROOT_PASSWORD="$(openssl rand -base64 32)"

oc create namespace openshift-logging --dry-run=client -o yaml | oc apply -f -

oc -n openshift-logging create secret generic minio-credentials \
  --from-literal=root-user="${MINIO_ROOT_USER}" \
  --from-literal=root-password="${MINIO_ROOT_PASSWORD}" \
  --dry-run=client -o yaml | oc apply -f -

oc -n openshift-logging create secret generic loki-s3 \
  --from-literal=access_key_id="${MINIO_ROOT_USER}" \
  --from-literal=access_key_secret="${MINIO_ROOT_PASSWORD}" \
  --from-literal=bucketnames=loki \
  --from-literal=endpoint=http://minio.openshift-logging.svc:9000 \
  --from-literal=region=us-east-1 \
  --dry-run=client -o yaml | oc apply -f -
```

### 4.2 Keycloak

```bash
oc create namespace keycloak-dev --dry-run=client -o yaml | oc apply -f -

oc -n keycloak-dev create secret generic keycloak-db-secret \
  --from-literal=username=keycloak \
  --from-literal=password="$(openssl rand -base64 32)" \
  --from-literal=database=keycloak \
  --dry-run=client -o yaml | oc apply -f -

cd "${WORKDIR}/keycloak-gitops"
cp -n .env.example .env
scripts/bootstrap-observability-users.sh
```

O script cria `keycloak-dev/keycloak-observability-users`, usado pelo Job que
importa o realm `observability`.

### 4.3 Zabbix

```bash
oc create namespace zabbix --dry-run=client -o yaml | oc apply -f -

oc -n zabbix create secret generic zabbix-db \
  --from-literal=username=zabbix \
  --from-literal=password="$(openssl rand -base64 32)" \
  --from-literal=database=zabbix \
  --dry-run=client -o yaml | oc apply -f -
```

O Secret `grafana/zabbix-datasource` será criado depois pelo bootstrap do
Zabbix, quando a API estiver disponível.

## 5. Subir o OpenShift GitOps

Na primeira instalação, não aplique `overlays/cluster` diretamente. Esse
overlay contém a `ArgoCD` CR, mas a CRD `argocds.argoproj.io` só aparece depois
que o Operator instalado pelo OLM termina de subir. Se tudo for aplicado em uma
única chamada, o `oc` pode retornar:

```text
no matches for kind "ArgoCD" in version "argoproj.io/v1beta1"
ensure CRDs are installed first
```

Use o bootstrap em fases:

```bash
cd "${WORKDIR}/argocd-gitops"
scripts/bootstrap-openshift-gitops.sh

oc -n openshift-gitops wait --for=condition=Available \
  deployment/openshift-gitops-server --timeout=10m

oc -n openshift-gitops get pods,route
```

O script é idempotente: reaplica `Namespace`, `OperatorGroup` e `Subscription`,
aguarda a CRD `argocds.argoproj.io`, aplica a `ArgoCD` CR e espera o servidor
ficar disponível. Depois disso, o app `argocd-cluster` pode reconciliar
`overlays/cluster` normalmente.

## 6. Aplicar o app-of-apps local

```bash
cd "${WORKDIR}/argocd-gitops"
oc apply -k overlays/desenvolvimento
```

O `platform-apps` cria as `Application` dos demais repositórios. Todas as
aplicações versionadas usam sync automático:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

Acompanhe a sincronização:

```bash
oc -n openshift-gitops get applications.argoproj.io
watch 'oc -n openshift-gitops get applications.argoproj.io'
```

Se quiser forçar novo refresh após um push:

```bash
oc -n openshift-gitops annotate application platform-apps \
  argocd.argoproj.io/refresh=hard --overwrite
```

## 7. Bootstraps pós-sync

### 7.1 Grafana OAuth via Keycloak

Execute depois que o Keycloak estiver saudável e o Job do realm tiver rodado:

```bash
oc -n keycloak-dev get keycloak,pods,route

cd "${WORKDIR}/grafana-gitops"
cp -n .env.example .env
scripts/bootstrap-grafana-oauth.sh
```

Isso cria `grafana/grafana-oauth` com `client-id` e `client-secret` do client
`grafana` no Keycloak.

Depois, force o sync/restart do Grafana se ele já tiver tentado subir sem o
Secret:

```bash
oc -n openshift-gitops annotate application grafana \
  argocd.argoproj.io/refresh=hard --overwrite
oc -n grafana rollout restart deployment/grafana-deployment 2>/dev/null || true
```

Se o Argo CD exibir `Sync failed` com retry esgotado depois que o Secret já
existe, dispare uma nova operação de sync pela própria `Application`:

```bash
APP=grafana
REV="$(oc -n openshift-gitops get application "${APP}" \
  -o jsonpath='{.status.sync.revision}')"

oc -n openshift-gitops patch application "${APP}" --type=merge -p \
  "{\"operation\":{\"initiatedBy\":{\"username\":\"manual\"},\"sync\":{\"revision\":\"${REV}\",\"prune\":true,\"syncOptions\":[\"CreateNamespace=true\",\"SkipDryRunOnMissingResource=true\",\"PruneLast=true\"]}}}"

oc -n openshift-gitops get application "${APP}"
```

Esse cenário costuma acontecer quando a primeira tentativa falha por uma
dependência temporária, como `grafana/grafana-oauth` ainda ausente.

### 7.2 Zabbix API, SAML e datasource do Grafana

Defina a senha administrativa atual do Zabbix no `.env` do repo:

```bash
cd "${WORKDIR}/zabbix-gitops"
cp -n .env.example .env
```

Edite `.env` e preencha:

```dotenv
ZABBIX_ADMIN_PASSWORD=<senha-admin-atual>
```

Então execute:

```bash
scripts/bootstrap-zabbix.sh
```

O bootstrap cria ou atualiza:

- usuário técnico `grafana-datasource`;
- grupo `Grafana datasource readers`;
- Secret `grafana/zabbix-datasource`;
- SAML do Zabbix apontando para Keycloak;
- hosts e web scenarios HTTP para OpenShift API, Argo CD, Keycloak, Grafana e Zabbix.

Sem o Secret `grafana/zabbix-datasource`, o `GrafanaDatasource` do Zabbix pode
ser criado pelo Operator, mas ficará sem credenciais para consultar a API do
Zabbix. Reexecute `scripts/bootstrap-zabbix.sh` sempre que recriar o namespace
`grafana`, rotacionar a senha/token técnico ou reconstruir o ambiente.

## 8. Validar a stack

```bash
oc -n openshift-gitops get applications.argoproj.io
oc get ns keycloak-dev grafana zabbix observability observability-apps tempo openshift-logging
oc -n observability-apps get monitoringstack,pods,svc,pvc
oc -n pyroscope get statefulset,pods,svc,pvc,servicemonitor
oc -n grafana get grafana,grafanadatasource,grafanadashboard,route
oc -n tempo get tempomonolithic,pods,svc,pvc
oc -n observability get opentelemetrycollector,pods,svc,servicemonitor
oc -n zabbix get pods,svc,route
```

Valide os datasources do Grafana pela UI ou API. O health check do Tempo pode
retornar `404` no endpoint `/api/echo` do gateway multi-tenant do Operator; isso
não significa necessariamente que queries reais de trace falharam.

## 9. Drilldown no Grafana

O Grafana fica provisionado com:

- Prometheus/Thanos: métricas do OpenShift e workloads;
- Prometheus Apps: métricas de aplicações, span metrics e exemplares;
- Pyroscope: profiles e datasource para Profiles Drilldown;
- Loki: logs e derived field `trace_id` → Tempo;
- Tempo: TraceQL, `tracesToLogsV2`, `tracesToMetrics`, `nodeGraph` e `serviceMap`;
- Zabbix: plugin `alexanderzobnin-zabbix-app`.

No CRC, o caminho suportado é:

```text
Aplicação -> OpenTelemetry Collector -> TempoMonolithic
                              └-------> Prometheus Apps: traces_span_metrics_*
Grafana -> Tempo/Loki/Prometheus/Zabbix
```

O Red Hat OpenTelemetry Collector 0.152.1 validado neste ambiente possui
`span_metrics`, mas não possui connector `servicegraph`. Por isso:

- Traces Drilldown/TraceQL e links trace → logs/métricas ficam preparados;
- Service Graph fica configurado no datasource, mas só mostrará dados se houver
  métricas `traces_service_graph_*`;
- para Service Graph completo, evolua para TempoStack com object storage e
  metrics-generator, ou adicione Grafana Alloy/collector compatível.
- Profiles Drilldown usa o backend Pyroscope. Sem aplicações instrumentadas, o
  datasource fica pronto, mas ainda não haverá flamegraphs nem correlação trace
  → profile.

Valide os componentes do collector:

```bash
oc -n observability exec deploy/otel-collector-collector -- \
  /usr/bin/opentelemetry-collector components
```

Para diagnóstico de erros como `undefined` ou `duration > }` no Traces
Drilldown, veja `grafana-gitops/docs/DRILLDOWN.md`. Em geral, essas mensagens
indicam estado/filtros vazios na UI; queries TraceQL válidas devem retornar 200
no Tempo.

## 10. Network Observability opcional

O Network Observability permanece opt-in porque usa eBPF, coleta em nível de
cluster e consome recursos extras no CRC.

Para habilitar:

```bash
cd "${WORKDIR}/argocd-gitops"
oc apply -k optional
```

Políticas aplicadas no repo `network-observability-gitops`:

- `spec.networkPolicy.enable: true`;
- `deploymentModel: Direct`;
- `agent.ebpf.sampling: 100`;
- métricas reduzidas para controlar cardinalidade;
- documentação em `network-observability-gitops/docs/POLITICAS.md`.

Valide:

```bash
oc get flowcollector cluster
oc -n netobserv get pods
oc adm top pods -n netobserv
```

## 11. Reexecutar, limpar e diagnosticar

Reexecutar é seguro: os scripts usam criação idempotente de Secret/API sempre
que possível.

Forçar sync de um app:

```bash
oc -n openshift-gitops annotate application <app> \
  argocd.argoproj.io/refresh=hard --overwrite
```

Ver diff/sync pelo Argo CD:

```bash
oc -n openshift-gitops get application <app> -o yaml
```

Remover somente o opcional:

```bash
oc -n openshift-gitops delete application network-observability
```

Remover o CRC inteiro:

```bash
crc stop
crc delete
```

## 12. Limitações do CRC

- Single-node, sem alta disponibilidade.
- PVC local e capacidade limitada.
- Tempo usa `TempoMonolithic`; `TempoStack` exige object storage suportado.
- Network Observability aumenta uso de CPU/memória.
- Alguns Operators demoram para instalar CRDs; `SkipDryRunOnMissingResource`
  está configurado onde necessário.
- Rotas usam certificados locais do CRC; em produção revise TLS, CA, cookies e
  headers.
