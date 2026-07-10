# Ambientes

Este repositório gerencia o Argo CD/OpenShift GitOps e o app-of-apps da plataforma.

- `overlays/desenvolvimento`: cria o app-of-apps que aponta para `overlays/desenvolvimento` dos demais repos.
- `overlays/aceite`: cria o app-of-apps que aponta para `overlays/aceite`.
- `overlays/producao`: cria o app-of-apps que aponta para `overlays/producao`.
- `overlays/applications/*`: renderiza as `Application` dos componentes para cada ambiente.
- `optional/acm`: gera `Application` por cluster/ambiente via `ApplicationSet`
  para uso com Red Hat Advanced Cluster Management.

Validação:

```bash
oc kustomize overlays/desenvolvimento >/tmp/argocd-dev.yaml
oc kustomize overlays/aceite >/tmp/argocd-aceite.yaml
oc kustomize overlays/producao >/tmp/argocd-prod.yaml
oc kustomize overlays/applications/desenvolvimento >/tmp/apps-dev.yaml
oc apply --dry-run=client -k overlays/desenvolvimento
```

Decisões:

- O ambiente CRC usa `desenvolvimento`.
- O `Application` `argocd-cluster` continua apontando para `overlays/cluster`, pois representa a instalação do próprio OpenShift GitOps.
- `network-observability` permanece opt-in em `optional/` por consumir recursos adicionais.
- `prometheus-apps` é sincronizado antes do Grafana para disponibilizar o
  datasource de métricas de aplicações e exemplares.
- Em ACM, não reutilize nomes simples como `grafana` ou `zabbix` para vários
  clusters no mesmo Argo CD. Use o padrão do `optional/acm`:
  `<cluster-normalizado>-<ambiente>-<componente>`.
