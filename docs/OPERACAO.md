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

## Limites de autorização

O AppProject service-mesh limita repositório, namespaces e tipos aceitos pela Application. O controlador da plataforma ainda possui o vínculo global de bootstrap em base/clusterrolebinding.yaml. Remover cluster-admin sem inventariar namespaces, CRDs, RBAC e auto-gerenciamento pode impedir reconciliação ou reversão. Para restringi-lo, derive uma lista dos recursos de todas as Applications, prepare Roles/ClusterRoles específicas e valide criação, atualização e remoção em ambiente descartável antes da troca. Não tratar AppProject como barreira IAM equivalente ao RBAC da API.
