# Service Mesh com Kiali

Este perfil mantém a Application `service-mesh` e seleciona `service-mesh-gitops/optional/kiali`, reunindo infraestrutura e Kiali na mesma sincronização. Não aplique o perfil sem Kiali em seguida, pois ele substitui a fonte desta Application.

```bash
oc apply -k optional/service-mesh-kiali
oc -n openshift-gitops get application service-mesh
oc -n istio-system get kiali,pods,route
oc -n istio-system get route kiali -o jsonpath='https://{.spec.host}{"\n"}'
```

O auto-sync e o self-heal permanecem habilitados, sem prune automático. O AppProject permite adicionalmente o recurso Kiali e a NetworkPolicy que libera acesso específico ao Prometheus em `observability-apps`. O perfil padrão `optional/service-mesh` continua sem Kiali.

A autenticação utiliza o OpenShift e seu IdP existente. A interface é somente de leitura, com descoberta restrita aos namespaces selecionados. O operador cria os recursos da instância, incluindo Deployment, Service e Route; não cadastre esses mesmos recursos separadamente no Argo CD.

Consulte [instalação, acesso, diagnóstico e remoção](https://github.com/thiagobotelho/service-mesh-gitops/blob/main/docs/KIALI.md). As aplicações dos exercícios continuam fora do Argo CD.
