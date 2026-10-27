# Operação do Argo CD

Consulte Applications, fontes e condições antes de sincronizar:

```bash
oc -n openshift-gitops get applications.argoproj.io
oc -n openshift-gitops get application <aplicacao> -o yaml
```

Revise o diff, a revisão de origem e os recursos sujeitos a prune. Quando necessário, solicite nova comparação:

```bash
oc -n openshift-gitops annotate application <aplicacao> argocd.argoproj.io/refresh=hard --overwrite
```

Operators e CRDs exigem instalação por fases. Para módulos opcionais de Service Mesh, siga [optional/service-mesh](../optional/service-mesh/README.md). O cadastro de uma Application manual não executa sua instalação. Para autenticação do console OpenShift, consulte [AUTENTICACAO-KEYCLOAK-CRC.md](AUTENTICACAO-KEYCLOAK-CRC.md).
