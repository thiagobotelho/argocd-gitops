# Acesso OpenShift por grupos do Keycloak

Aplique com uma sessão administrativa após configurar o provedor `keycloak`
e criar os namespaces da stack:

```bash
oc kustomize bootstrap/openshift-access
oc apply -k bootstrap/openshift-access
```

| Grupo | Role | Namespaces |
| --- | --- | --- |
| openshift-viewers | view | grafana, zabbix, tempo, pyroscope, observability, observability-apps |
| openshift-project-admins | admin | Os mesmos seis namespaces |

`view` não permite ler Secrets ou alterar workloads. `admin` permite ler
Secrets, gerenciar workloads e RBAC permitido dentro desses namespaces.
O entrypoint de projetos não concede `cluster-admin`, edição de SCC, nós ou administração dos namespaces
`openshift-gitops`, `keycloak-dev` e dos operadores. Não inclua namespaces de
controladores privilegiados nessa lista sem revisar suas ServiceAccounts.

O bootstrap não cria namespaces, usuários ou objetos Group. Os grupos e a
associação inicial de `observability-admin` estão em `keycloak-gitops`.
A sincronização OIDC ocorre no login. Use a senha atual; mantenha uma sessão
kubeadmin para a conferência. O grupo `openshift-cluster-admins` contém a conta dedicada `openshift-admin`;
seu vínculo global é aplicado separadamente.

Os arquivos não fazem parte do App-of-Apps. A aplicação é manual, como o
bootstrap do provedor OAuth; mantenha alterações versionadas. Um membro de
`openshift-project-admins` pode alterar o RBAC local; revise drift quando
reaplicar esses arquivos. Credenciais e acesso à interface Argo são separados.

## Conferir RBAC

Com uma sessão administrativa, execute testes por impersonação. Eles verificam
as permissões dos grupos e não substituem o login SSO real:

```bash
oc auth can-i get pods -n grafana --as=leitor-sintetico --as-group=openshift-viewers
oc auth can-i get secrets -n grafana --as=leitor-sintetico --as-group=openshift-viewers
oc auth can-i create deployments.apps -n grafana --as=leitor-sintetico --as-group=openshift-viewers
oc auth can-i create deployments.apps -n grafana --as=admin-sintetico --as-group=openshift-project-admins
oc auth can-i create clusterrolebindings.rbac.authorization.k8s.io --as=admin-sintetico --as-group=openshift-project-admins
oc auth can-i get secrets -n keycloak-dev --as=admin-sintetico --as-group=openshift-project-admins
```

Resultado: `yes`, `no`, `no`, `yes`, `no`, `no`. Para conferir autenticação,
abra uma janela privada, escolha Keycloak no console e entre como
`observability-admin`. Confira projetos disponíveis, ações permitidas e logout.
Mantenha `kubeadmin` até concluir os testes.

## Remover acesso

Primeiro remova o membro do grupo no Keycloak e encerre suas sessões. Para
remover os vínculos inteiros, como administrador:

```bash
oc delete -k bootstrap/openshift-access
```

Isso remove somente os doze RoleBindings declarados, sem excluir projetos ou
volumes. A remoção de um membro não invalida necessariamente todos os tokens
já emitidos; confira as sessões e sua validade antes de considerar o acesso
revogado. Administração global exige decisão e vínculo próprios.

## Administração global e Argo CD

A conta `openshift-admin` do Keycloak é destinada à administração do cluster.
Aplique o vínculo global somente com uma sessão administrativa:

```bash
oc kustomize bootstrap/openshift-access/cluster-admin
oc apply -k bootstrap/openshift-access/cluster-admin
```

O grupo `openshift-cluster-admins` recebe `cluster-admin`, incluindo acesso a
Secrets, SCC, RBAC e namespaces de sistema. O papel independe dos vínculos de
projeto. Preserve kubeadmin até concluir login e conferência das permissões.

O Argo usa Dex com OpenShift OAuth. No botão de login pelo OpenShift, escolha
o provedor `keycloak` e entre como `openshift-admin`. O grupo é mapeado para
`role:admin` em `base/argocd.yaml`; os demais usuários continuam readonly por
padrão. Esse fluxo não exige outro client Keycloak exclusivo do Argo. O admin
local do Argo continua disponível para recuperação.

Para remover somente a concessão global:

```bash
oc delete -k bootstrap/openshift-access/cluster-admin
```

Revise também a associação no Keycloak, o mapeamento de administração no Argo
e as sessões/tokens existentes. Não remova os acessos de recuperação antes de
confirmar outro administrador funcional.
