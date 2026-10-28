# Tutorial CRC/OpenShift Local da stack GitOps

## 1. Antes de começar

Execute as etapas em ordem, um comando por vez, em Bash ou Zsh. Pare se um comando falhar ou a verificação indicada não passar.

Crie Secrets somente quando estiverem ausentes. Preserve senhas e dados existentes. Execute consultas de credenciais em terminal privado, sem gravação nem `set -x`; não publique as saídas.

## 2. Preparar o host e as fontes

### 2.1 Ferramentas e capacidade

```bash
printf 'Bash: %s | Zsh: %s\n' "${BASH_VERSION:-não ativo}" "${ZSH_VERSION:-não ativo}"
git --version
crc version
openssl version
curl --version
```

Reserve 10 vCPUs, 40 GiB de RAM e 200 GiB de disco para a VM, além dos recursos do host. O `oc` será disponibilizado pelo CRC após o start.

Execute `crc` no host que administra a VM, sem `sudo`. Se a VM está no Windows, execute os comandos CRC no Windows e use o WSL para o `oc`.

Mantenha o mesmo terminal durante cada leitura de senha e criação do Secret correspondente.

Digite a senha quando o prompt aguardar. Aguarde a leitura terminar antes de colar o próximo comando.

### 2.2 Escolher um diretório novo

```bash
export WORKDIR="$HOME/labs/openshift-local-stack"
mkdir -p "$WORKDIR"
cd "$WORKDIR"
```

Use um diretório novo. Se escolher outro caminho, mantenha o mesmo valor de `WORKDIR` nas etapas seguintes.

### 2.3 Clonar cada repositório

```bash
git clone --branch main --single-branch https://github.com/thiagobotelho/openshift-local-installer.git
git clone --branch main --single-branch https://github.com/thiagobotelho/argocd-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/metallb-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/prometheus-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/pyroscope-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/loki-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/tempo-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/opentelemetry-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/keycloak-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/grafana-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/zabbix-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/network-observability-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/service-mesh-gitops.git
git clone --branch main --single-branch https://github.com/thiagobotelho/mesh-apps-lab.git
```

Confirme que todos os clones terminaram sem erro. Para repositórios privados, configure autenticação Git local. Em forks, ajuste os `repoURL` das Applications.

Confira as referências dos projetos antes de instalar:

```bash
git -C "$WORKDIR/argocd-gitops" log -1 --oneline
git -C "$WORKDIR/metallb-gitops" log -1 --oneline
git -C "$WORKDIR/keycloak-gitops" log -1 --oneline
```

Registre os SHAs usados na validação. As Applications acompanham `main`.

## 3. Criar o CRC

### 3.1 Excluir o CRC anterior — somente se necessário

Execute os comandos abaixo somente para excluir um CRC existente. Faça backup antes: `crc delete` remove o cluster e seus volumes. Em uma instalação nova, avance para 3.2.

```bash
crc stop
crc delete
```

### 3.2 Definir o perfil e iniciar

```bash
crc config set preset openshift
crc config set cpus 10
crc config set memory 40960
crc config set disk-size 200
crc config set enable-cluster-monitoring true
crc setup
crc start
```

Informe o pull secret Red Hat quando solicitado e aguarde `crc start` terminar. Mantenha o pull secret fora do Git.

### 3.3 Autenticar e isolar o kubeconfig

No host que administra a VM, consulte as credenciais:

```bash
crc console --credentials
```

```bash
umask 077
export KUBECONFIG="$WORKDIR/kubeconfig-crc"
eval "$(crc oc-env)"
oc login -u kubeadmin https://api.crc.testing:6443
oc whoami
oc whoami --show-server
oc get nodes
```

Use a senha no prompt de `oc login`. No WSL, consulte as credenciais no host Windows responsável pela VM.

Mantenha o kubeconfig fora do Git. Ao abrir outro terminal, redefina `WORKDIR` e `KUBECONFIG`. Para a interface do Argo CD, use o usuário local `admin` da etapa 5.3.

Confira: servidor `https://api.crc.testing:6443`, usuário `kubeadmin` e nó `Ready`.

### 3.4 Verificar a plataforma e o armazenamento

```bash
oc get clusterversion
oc get clusteroperators
oc get storageclass
oc -n openshift-monitoring get pods
```

Aguarde os operadores habilitados estabilizarem. Investigue `Degraded=True` persistente antes de continuar.

Confira a StorageClass `crc-csi-hostpath-provisioner` e os pods do monitoramento. Se a classe for diferente, ajuste os overlays antes da instalação.

## 4. Preparar namespaces e Secrets iniciais

### 4.1 Criar os namespaces necessários ao bootstrap

```bash
oc create namespace openshift-logging
oc create namespace keycloak-dev
oc create namespace zabbix
oc create namespace grafana
```

Se aparecer `AlreadyExists`, confirme o namespace e continue sem excluí-lo.

### 4.2 MinIO e acesso S3 do Loki

Confira primeiro se já existem:

```bash
oc -n openshift-logging get secret minio-credentials --ignore-not-found
oc -n openshift-logging get secret loki-s3 --ignore-not-found
```

Se algum Secret já existir, pare e confira sua utilização antes de criar ou alterar credenciais.

```bash
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD="$(openssl rand -base64 32)"
oc -n openshift-logging create secret generic minio-credentials \
  --from-literal=root-user="$MINIO_ROOT_USER" \
  --from-file=root-password=<(printf '%s' "$MINIO_ROOT_PASSWORD")
oc -n openshift-logging create secret generic loki-s3 \
  --from-literal=access_key_id="$MINIO_ROOT_USER" \
  --from-file=access_key_secret=<(printf '%s' "$MINIO_ROOT_PASSWORD") \
  --from-literal=bucketnames=loki \
  --from-literal=endpoint=http://minio.openshift-logging.svc:9000 \
  --from-literal=region=us-east-1
unset MINIO_ROOT_PASSWORD MINIO_ROOT_USER
```

Os dois Secrets devem usar a mesma senha MinIO. Se uma criação falhar, corrija antes de executar `unset`.

```bash
oc -n openshift-logging describe secret minio-credentials
oc -n openshift-logging describe secret loki-s3
```

Confira as chaves dos Secrets e seus tamanhos; os valores não devem aparecer na saída.

### 4.3 Banco do Keycloak

```bash
oc -n keycloak-dev get secret keycloak-db-secret --ignore-not-found
```

Se estiver ausente na instalação nova:

```bash
KEYCLOAK_DB_PASSWORD="$(openssl rand -base64 32)"
oc -n keycloak-dev create secret generic keycloak-db-secret \
  --from-literal=username=keycloak \
  --from-file=password=<(printf '%s' "$KEYCLOAK_DB_PASSWORD") \
  --from-literal=database=keycloak
unset KEYCLOAK_DB_PASSWORD
oc -n keycloak-dev describe secret keycloak-db-secret
```

Confira as chaves `username`, `password` e `database`. Em banco existente, coordene qualquer troca de senha com o PostgreSQL.

### 4.4 Senhas iniciais dos usuários do realm

Escolha senhas distintas para os três usuários e guarde-as no gerenciador de senhas.

```bash
oc -n keycloak-dev get secret keycloak-observability-users --ignore-not-found
```

Se estiver ausente:

```bash
printf '%s' 'Senha inicial de grafana-admin: '
IFS= read -r -s GRAFANA_ADMIN_PASSWORD
printf '\n'
printf '%s' 'Senha inicial de zabbix-admin: '
IFS= read -r -s ZABBIX_ADMIN_PASSWORD
printf '\n'
printf '%s' 'Senha inicial de observability-admin: '
IFS= read -r -s OBSERVABILITY_ADMIN_PASSWORD
printf '\n'
test -n "$GRAFANA_ADMIN_PASSWORD"
test -n "$ZABBIX_ADMIN_PASSWORD"
test -n "$OBSERVABILITY_ADMIN_PASSWORD"
```

Se algum `test -n` falhar, leia novamente a senha correspondente. Confira o preenchimento:

```bash
test -n "$GRAFANA_ADMIN_PASSWORD" && printf 'Grafana: preenchida\n'
test -n "$ZABBIX_ADMIN_PASSWORD" && printf 'Zabbix: preenchida\n'
test -n "$OBSERVABILITY_ADMIN_PASSWORD" && printf 'Observability: preenchida\n'
```

Avance somente quando aparecerem as três confirmações.

```bash
oc -n keycloak-dev create secret generic keycloak-observability-users \
  --from-file=GRAFANA_ADMIN_PASSWORD=<(printf '%s' "$GRAFANA_ADMIN_PASSWORD") \
  --from-file=ZABBIX_ADMIN_PASSWORD=<(printf '%s' "$ZABBIX_ADMIN_PASSWORD") \
  --from-file=OBSERVABILITY_ADMIN_PASSWORD=<(printf '%s' "$OBSERVABILITY_ADMIN_PASSWORD")
unset GRAFANA_ADMIN_PASSWORD ZABBIX_ADMIN_PASSWORD OBSERVABILITY_ADMIN_PASSWORD
oc -n keycloak-dev describe secret keycloak-observability-users
```

Use essas senhas nos logins de `grafana-admin`, `zabbix-admin` e `observability-admin`. Se já foram alteradas pela UI, use as senhas atuais.

### 4.5 Banco do Zabbix

```bash
oc -n zabbix get secret zabbix-db --ignore-not-found
```

Se estiver ausente:

```bash
ZABBIX_DB_PASSWORD="$(openssl rand -base64 32)"
oc -n zabbix create secret generic zabbix-db \
  --from-literal=username=zabbix \
  --from-file=password=<(printf '%s' "$ZABBIX_DB_PASSWORD") \
  --from-literal=database=zabbix
unset ZABBIX_DB_PASSWORD
oc -n zabbix describe secret zabbix-db
```

### 4.6 MetalLB no CRC

Não há comando nesta etapa. O App-of-Apps configura o MetalLB automaticamente no perfil CRC, usando a faixa `.200–.250` da rede IPv4 do nó.

Use somente em rede de laboratório com essa faixa disponível. Para aceite e produção, configure a faixa explicitamente.

### 4.7 Senha inicial do administrador OpenShift

Escolha uma senha própria para `openshift-admin`. Confira o Secret:

```bash
oc -n keycloak-dev get secret keycloak-openshift-users --ignore-not-found
```

Se estiver ausente:

```bash
printf '%s' 'Senha inicial de openshift-admin: '
IFS= read -r -s OPENSHIFT_ADMIN_PASSWORD
printf '\n'
test -n "$OPENSHIFT_ADMIN_PASSWORD"
```

Com a senha preenchida:

```bash
oc -n keycloak-dev create secret generic keycloak-openshift-users \
  --from-file=OPENSHIFT_ADMIN_PASSWORD=<(printf '%s' "$OPENSHIFT_ADMIN_PASSWORD")
unset OPENSHIFT_ADMIN_PASSWORD
```

Preserve o Secret existente; esse passo não é rotação de senha.

## 5. Instalar OpenShift GitOps

### 5.1 Conferir os manifests e instalar o Operator

```bash
cd "$WORKDIR/argocd-gitops"
cat base/subscription.yaml
oc apply -f base/namespace.yaml
oc apply -f base/operatorgroup.yaml
oc apply -f base/subscription.yaml
oc -n openshift-gitops-operator get subscription,installplan,csv
```

Confira o canal e o catálogo em `base/subscription.yaml` antes de aplicar. O Operator usa `openshift-gitops-operator`; a instância usa `openshift-gitops`.

Aguarde o CSV ficar `Succeeded`. Se falhar, consulte Subscription, InstallPlan e eventos do namespace.

### 5.2 Aguardar a CRD e criar a instância

```bash
oc get crd argocds.argoproj.io
```

Somente depois de a CRD aparecer:

```bash
oc wait --for=condition=Established crd/argocds.argoproj.io --timeout=10m
oc apply -f base/argocd.yaml
oc apply -f base/clusterrolebinding.yaml
oc -n openshift-gitops get deployments
```

Aplique a instância somente após a CRD ficar `Established`. O ClusterRoleBinding abaixo concede `cluster-admin` ao controller para o laboratório.

Quando o deployment existir:

```bash
oc -n openshift-gitops wait --for=condition=Available deployment/openshift-gitops-server --timeout=10m
oc -n openshift-gitops get pods,route
```

Confira o servidor disponível e a Route criada.

### 5.3 Consultar o acesso administrativo local do Argo CD

Consulte o endereço:

```bash
oc -n openshift-gitops get route openshift-gitops-server \
  -o jsonpath='{.spec.host}{"\n"}'
```

Abra `https://<host-da-route>`. Consulte a senha local do Argo:

```bash
oc -n openshift-gitops get secret openshift-gitops-cluster \
  -o jsonpath='{.data.admin\.password}' | base64 --decode
printf '\n'
```

A saída contém a senha. Consulte somente em terminal privado.

Entre pelo formulário local com **Username: admin** e a senha consultada. Confira `admin` em **User Info**.

Se a senha já foi alterada, use a atual. Se o admin local estiver desabilitado, use uma conta autorizada da instalação.

### 5.4 Validar o acesso às fontes Git e imagens

No Argo, abra **Settings > Repositories**, cadastre as fontes privadas usadas pelas Applications e confirme a conexão. Use credenciais de leitura; mantenha tokens fora de URLs e do Git.

Para imagens privadas, configure o pull secret no namespace consumidor e vincule-o à ServiceAccount antes da instalação.

## 6. Iniciar a stack base pelo App-of-Apps

### 6.1 Renderizar antes de aplicar

```bash
cd "$WORKDIR/argocd-gitops"
oc kustomize overlays/desenvolvimento
oc kustomize overlays/applications/desenvolvimento
```

Confira `repoURL`, `targetRevision`, `path` e `destination` nas duas saídas.

### 6.2 Aplicar e acompanhar

```bash
oc apply -k overlays/desenvolvimento
oc -n openshift-gitops get applications.argoproj.io
```

Confira o diff antes de aplicar. Autosync, prune e selfHeal podem criar, alterar e remover recursos conforme o Git.

Acompanhe as Applications. O Grafana pode aguardar o Secret `grafana-oauth`, criado na etapa 8.

### 6.3 Consultar falhas de sincronização

Para a aplicação Grafana:

```bash
oc -n openshift-gitops get application grafana -o jsonpath='{.status.conditions}'
oc -n openshift-gitops get application grafana -o jsonpath='{.status.operationState.message}'
oc -n grafana get pods,pvc,events
```

Para `no matches for kind GrafanaDashboard/GrafanaFolder`, confira o Operator e as CRDs:

```bash
oc get crd grafanas.grafana.integreatly.org grafanafolders.grafana.integreatly.org grafanadashboards.grafana.integreatly.org
oc -n grafana-operator get subscription,installplan,csv,pods
```

Aguarde as CRDs ficarem `Established`. Depois de corrigir a causa, use **Refresh → Sync completo** no Argo para repetir uma operação que falhou.

### 6.4 Acompanhar as imagens automáticas do MinIO e do cliente mc

Execute **Sync completo** de `loki` no Argo. Aguarde o hook `crc-minio-images` concluir.

Confira o registro integrado, as BuildConfigs e o andamento:

```bash
oc get clusteroperator image-registry
oc -n openshift-image-registry get pods
oc -n openshift-logging get buildconfig,build,imagestream
oc -n openshift-logging get job crc-minio-images
oc -n openshift-logging logs job/crc-minio-images
```

Confira o registro disponível e o hook em execução ou concluído. Builds ativos e imagens publicadas são reutilizados.

Após o hook concluir, confira as tags publicadas:

```bash
oc -n openshift-logging get imagestreamtag minio-crc:RELEASE.2025-09-07T16-13-09Z
oc -n openshift-logging get imagestreamtag mc-crc:RELEASE.2025-08-13T08-35-41Z
```

Confirme que as duas tags existem. Depois acompanhe o MinIO:

```bash
oc -n openshift-logging rollout status deployment/minio --timeout=10m
oc -n openshift-logging get jobs,pods
```

Confira o MinIO pronto e o Job de bucket concluído. Em falha, consulte o log do hook, os eventos e os logs do build indicado em `get builds`.

Para repetir após corrigir uma falha, use **Refresh → Sync completo** de `loki`. Preserve o PVC `minio-data`.

Para alterar versões das imagens, siga o [procedimento do Loki](https://github.com/thiagobotelho/loki-gitops#imagens-automáticas-no-crc).

## 7. Validar Keycloak e preparar confiança TLS

### 7.1 Aguardar o Keycloak e o realm

```bash
oc -n keycloak-dev get keycloak,pods,jobs,route
oc -n keycloak-dev wait --for=condition=Ready keycloak/keycloak-dev --timeout=10m
```

Depois de o Job existir:

```bash
oc -n keycloak-dev wait --for=condition=Complete job/keycloak-config-cli-observability --timeout=10m
```

Aguarde o Job de importação concluir. Acesse o console do Keycloak conforme 7.2.

No realm `observability`, confira os usuários `grafana-admin`, `zabbix-admin`, `observability-admin`, seus grupos e os clients `grafana`, `zabbix`, `openshift`.

### 7.2 Consultar o administrador inicial do Keycloak

Consulte o endereço público:

```bash
oc -n keycloak-dev get route keycloak -o jsonpath='{.spec.host}{"\n"}'
```

Abra `https://<host-da-route>/admin/`.

Consulte o nome do administrador inicial no seu terminal privado:

```bash
oc -n keycloak-dev get secret keycloak-dev-initial-admin \
  -o jsonpath='{.data.username}' | base64 --decode
printf '\n'
```

Depois consulte a senha no mesmo terminal:

```bash
oc -n keycloak-dev get secret keycloak-dev-initial-admin \
  -o jsonpath='{.data.password}' | base64 --decode
printf '\n'
```

Entre com o `username` e a senha consultados. A saída da consulta de senha é confidencial.

Selecione o realm **observability**.

Se a conta inicial foi removida ou a senha mudou, use o administrador permanente existente. Para recuperação, siga a [documentação do Keycloak](https://www.keycloak.org/server/bootstrap-admin-recovery).

Após o Job de importação concluir, inicialize somente senhas ausentes:

```bash
cd "$WORKDIR/keycloak-gitops"
git status --short
git pull --ff-only
python3 scripts/initialize-lab-passwords.py --initialize-missing
```

Resolva alterações locais antes do pull. Use os Secrets das etapas 4.4 e 4.7; senhas já configuradas são preservadas.

### 7.3 Obter a CA do ingress deste CRC

Crie o arquivo da CA pública do ingress padrão do CRC:

```bash
mkdir -p "$WORKDIR/certificados"
oc -n openshift-ingress-operator get secret router-ca -o jsonpath='{.data.tls\.crt}' \
  | base64 --decode > "$WORKDIR/certificados/ingress-ca.crt"
openssl x509 -in "$WORKDIR/certificados/ingress-ca.crt" -noout -subject -issuer -dates
KEYCLOAK_URL="https://$(oc -n keycloak-dev get route keycloak -o jsonpath='{.spec.host}')"
curl --fail --show-error --cacert "$WORKDIR/certificados/ingress-ca.crt" \
  "$KEYCLOAK_URL/realms/observability/.well-known/openid-configuration"
```

Para ingress com certificado customizado, use a CA correspondente. Exporte somente `tls.crt`; preserve a chave privada.

Confira a resposta OIDC sem erro TLS e `issuer` igual a `$KEYCLOAK_URL/realms/observability`.

## 8. Configurar Grafana OIDC manualmente

### 8.1 Conferir o client e transferir sua credencial

No Keycloak, abra **observability > Clients > grafana**. Habilite **Client authentication** e **Standard Flow**. Consulte o host do Grafana:

```bash
oc -n grafana get route grafana-route
```

Use `https://<host-da-route>/login/generic_oauth` em **Valid redirect URIs**. Em **Credentials**, copie o client secret atual. Confira o Secret consumidor:

```bash
oc -n grafana get secret grafana-oauth --ignore-not-found
```

Se ainda não existe:

```bash
printf '%s' 'Client secret do client grafana: '
IFS= read -r -s GRAFANA_CLIENT_SECRET
printf '\n'
test -n "$GRAFANA_CLIENT_SECRET"
```

Se o test passou:

```bash
oc -n grafana create secret generic grafana-oauth \
  --from-literal=client-id=grafana \
  --from-file=client-secret=<(printf '%s' "$GRAFANA_CLIENT_SECRET")
unset GRAFANA_CLIENT_SECRET
oc -n grafana describe secret grafana-oauth
```

Se o Secret já existir, confira sua correspondência com o client antes de atualizar.

### 8.2 Sincronizar e testar

No Argo, abra **grafana → Sync → Synchronize**, com todos os recursos selecionados. Acompanhe:

```bash
oc -n grafana get grafana,pods,route
oc -n openshift-gitops get application grafana
```

Teste o login Keycloak com `grafana-admin` em janela privada e confira o papel recebido. Conclua 9.3 antes de exigir o datasource Zabbix funcionando.

Após 9.3, confira o Job `grafana-enable-zabbix-app-plugin` concluído e o plugin Zabbix habilitado no Grafana.

## 9. Configurar Zabbix SAML/JIT

### 9.1 Preparar o acesso à API Zabbix

Atualize o repositório. Se `git status` listar alterações locais, resolva antes do pull:

```bash
cd "$WORKDIR/zabbix-gitops"
git status --short
git pull --ff-only
```

Confira as dependências, os workloads e a CA:

```bash
bash --version
python3 --version
curl --version
jq --version
openssl version
oc whoami
oc whoami --show-server
oc -n zabbix get pods,route
oc -n keycloak-dev get pods,route
openssl x509 -in "$WORKDIR/certificados/ingress-ca.crt" -noout -subject -issuer -dates
```

Continue com pods prontos, contexto do CRC e CA válida. Se `ingress-ca.crt` não existir, execute a etapa **7.3** antes de continuar.

Informe a senha atual do administrador **local do Zabbix**, normalmente `Admin`. Para instalação nova, faça o [primeiro login](https://www.zabbix.com/documentation/7.4/en/manual/quickstart/login) e altere a senha inicial antes de continuar.

```bash
printf '%s' 'Senha atual do administrador local Admin do Zabbix: '
IFS= read -r -s ZABBIX_ADMIN_PASSWORD
printf '\n'
test -n "$ZABBIX_ADMIN_PASSWORD"
```

Com a senha preenchida, configure:

```bash
export ZABBIX_ADMIN_PASSWORD
export BOOTSTRAP_CA_FILE="$WORKDIR/certificados/ingress-ca.crt"
export ZABBIX_ENABLE_SAML=true
export ZABBIX_ENABLE_SAML_JIT=true
export ZABBIX_MANAGE_SAML_IDP_CERT=true
export ZABBIX_MANAGE_GRAFANA_DATASOURCE=false
export ZABBIX_ENABLE_SAML_SCIM=false
```

Se o administrador local tiver outro nome, defina `ZABBIX_ADMIN_USER`. Mantenha SCIM desabilitado e a conta técnica do Grafana para 9.3.

Confira no Keycloak o client `zabbix` e seus mappers. Revise URLs e opções de eventual `.env` antes de executar.

### 9.2 Configurar SAML e JIT

A troca do certificado pode reiniciar o frontend e interromper sessões. Mantenha acesso administrativo local. Em caso de falha, corrija a etapa indicada antes de repetir.

Execute:

```bash
bash scripts/bootstrap-zabbix.sh
```

Confira a mensagem de reconciliação SAML concluída. Se houver certificado ambíguo ou diretório de outro IdP, pare e siga o [diagnóstico do bootstrap](https://github.com/thiagobotelho/zabbix-gitops#seleção-e-rotação-do-certificado-saml).

Após sucesso, remova as variáveis da sessão:

```bash
unset ZABBIX_ADMIN_PASSWORD BOOTSTRAP_CA_FILE
unset ZABBIX_ENABLE_SAML ZABBIX_ENABLE_SAML_JIT ZABBIX_MANAGE_SAML_IDP_CERT
unset ZABBIX_MANAGE_GRAFANA_DATASOURCE ZABBIX_ENABLE_SAML_SCIM
```

Confira os recursos e o certificado público que foi publicado:

```bash
oc -n zabbix get configmap zabbix-saml-idp
oc -n zabbix get configmap zabbix-saml-idp -o jsonpath='{.data.idp\.crt}' \
  | openssl x509 -noout -subject -issuer -dates -fingerprint -sha256
oc -n zabbix rollout status deployment/zabbix-web --timeout=5m
```

No Zabbix, abra **Users > Authentication > SAML** e confira:

| Campo | Valor esperado |
| --- | --- |
| IdP entity ID | URL Keycloak seguida de /realms/observability |
| SSO/SLO | URL Keycloak seguida de /realms/observability/protocol/saml |
| SP entity ID | zabbix |
| Username / grupos / nome / sobrenome | username / groups / firstName / lastName |
| Assertions assinadas / JIT | Habilitados |
| SCIM | Desabilitado neste procedimento |
| Grupo de desprovisionados | Disabled provisioned users, desabilitado |

| Grupo Keycloak | Grupo Zabbix | Role |
| --- | --- | --- |
| zabbix-super-admins / zabbix-admins | Zabbix administrators | Super admin role |
| zabbix-users / zabbix-guests | Grafana datasource readers | User role |

A execução substitui os mapeamentos do diretório conforme a tabela. No Keycloak, confira o ACS do client `zabbix`: `https://<host-do-zabbix>/index_sso.php?acs`, com o mapper `groups` sem caminho completo.

Teste `zabbix-admin` em janela privada. Confira grupo, role e logout; teste também um usuário sem mapeamento. Preserve o administrador local.

### 9.3 Criar o usuário técnico do datasource

No Zabbix, crie o usuário `grafana-datasource` com senha própria, grupo `Grafana datasource readers` e `User role`. Permita autenticação interna e as operações de leitura da API necessárias ao plugin.

Em **Host permissions**, conceda **Read** somente aos host groups que o Grafana deve consultar.

Transfira a mesma senha para o consumidor:

```bash
oc -n grafana get secret zabbix-datasource --ignore-not-found
```

Se estiver ausente:

```bash
printf '%s' 'Senha do usuário técnico grafana-datasource: '
IFS= read -r -s ZABBIX_DATASOURCE_PASSWORD
printf '\n'
test -n "$ZABBIX_DATASOURCE_PASSWORD"
```

Se o test passou:

```bash
oc -n grafana create secret generic zabbix-datasource \
  --from-literal=username=grafana-datasource \
  --from-file=password=<(printf '%s' "$ZABBIX_DATASOURCE_PASSWORD")
unset ZABBIX_DATASOURCE_PASSWORD
oc -n grafana describe secret zabbix-datasource
```

Sincronize **grafana** no Argo. No Grafana, teste o datasource Zabbix em **Save & test** ou faça uma consulta em **Explore**. Confira um item com valor recente e autorizado.

## 10. Configurar login OpenShift por Keycloak

Execute após o Keycloak estar estável. Preserve os provedores existentes e a sessão de `kubeadmin`.

### 10.1 Conferir o client e criar o Secret

No Keycloak, abra **observability > Clients > openshift**. Habilite **Client authentication** e **Standard Flow**; desabilite **Implicit Flow** e **Direct Access Grants**. Configure o callback:

```text
https://oauth-openshift.apps-crc.testing/oauth2callback/keycloak
```

Ajuste o domínio se necessário. Em **Credentials**, copie o client secret atual e confira o Secret consumidor:

```bash
oc -n openshift-config get secret keycloak-openshift-client-secret --ignore-not-found
```

Se ainda não existe:

```bash
printf '%s' 'Client secret do client openshift: '
IFS= read -r -s OPENSHIFT_CLIENT_SECRET
printf '\n'
test -n "$OPENSHIFT_CLIENT_SECRET"
```

Se o test passou:

```bash
oc -n openshift-config create secret generic keycloak-openshift-client-secret \
  --from-file=clientSecret=<(printf '%s' "$OPENSHIFT_CLIENT_SECRET")
unset OPENSHIFT_CLIENT_SECRET
oc -n openshift-config create configmap keycloak-issuer-ca \
  --from-file=ca.crt="$WORKDIR/certificados/ingress-ca.crt"
```

Use a CA validada na etapa 7.3.

### 10.2 Acrescentar o provedor sem apagar os existentes

```bash
oc get oauth cluster -o yaml
oc edit oauth cluster
```

Em `spec.identityProviders`, acrescente o item abaixo depois do provedor `developer`. Alinhe `- name: keycloak` com o `- htpasswd:` existente. Preserve os demais provedores, `tokenConfig` e `metadata`.

```yaml
- name: keycloak
  mappingMethod: claim
  type: OpenID
  openID:
    issuer: https://keycloak-dev.apps-crc.testing/realms/observability
    clientID: openshift
    clientSecret:
      name: keycloak-openshift-client-secret
    ca:
      name: keycloak-issuer-ca
    extraScopes:
      - email
      - profile
    claims:
      preferredUsername:
        - preferred_username
      name:
        - name
      email:
        - email
      groups:
        - groups
```

Confira `issuer` com a Route do Keycloak e salve a edição. Não aplique o arquivo `bootstrap/crc-keycloak-provider.yaml` sobre a configuração existente.

```bash
oc get clusteroperator authentication
oc -n openshift-authentication get pods
oc get oauth cluster -o jsonpath='{.spec.identityProviders[*].name}'
```

Aguarde `authentication` ficar disponível e sem degradação. Confira `developer keycloak` na lista de provedores. Teste o login Keycloak em janela privada e confira as permissões do usuário; mantenha a sessão de `kubeadmin` aberta.

### 10.3 Aplicar as permissões dos grupos

No Argo, sincronize **keycloak-dev** e aguarde o Job `keycloak-config-cli-observability` concluir.

| Grupo Keycloak | Membro inicial | Papel |
| --- | --- | --- |
| openshift-viewers | Nenhum | view nos seis namespaces da stack |
| openshift-project-admins | observability-admin | admin nos mesmos namespaces |
| openshift-cluster-admins | openshift-admin | cluster-admin com vínculo separado |

Aplique os vínculos com a sessão administrativa:

```bash
cd "$WORKDIR/argocd-gitops"
git status --short
git pull --ff-only
oc get namespace grafana zabbix tempo pyroscope observability observability-apps
oc kustomize bootstrap/openshift-access
oc apply -k bootstrap/openshift-access
```

Resolva alterações locais antes do pull. Confira os doze RoleBindings antes de aplicar. O papel admin de projeto permite ler Secrets e gerenciar recursos desses namespaces; atribua o grupo somente a operadores autorizados.

Aplique separadamente o acesso global da conta `openshift-admin`:

```bash
oc kustomize bootstrap/openshift-access/cluster-admin
oc apply -k bootstrap/openshift-access/cluster-admin
```

Esse vínculo concede administração completa do cluster. Mantenha kubeadmin até testar o novo administrador.

### 10.4 Testar o acesso pelo Keycloak

Abra o console OpenShift em janela privada, selecione **keycloak** e entre com **observability-admin**, usando sua senha atual. Confira o acesso a grafana, zabbix, tempo, pyroscope, observability e observability-apps.

Na sessão administrativa, confira a identidade e os grupos sincronizados:

```bash
oc get user observability-admin
oc get group openshift-project-admins -o yaml
oc auth can-i create deployments.apps -n grafana --as=observability-admin --as-group=openshift-project-admins
oc auth can-i create clusterrolebindings.rbac.authorization.k8s.io --as=observability-admin --as-group=openshift-project-admins
```

As duas últimas consultas devem retornar `yes` e `no`. Elas testam RBAC por impersonação; confirme separadamente o login na janela privada. Os grupos aparecem no OpenShift após login de seus membros.

Para leitura, associe uma conta autorizada ao grupo **openshift-viewers** no Keycloak e renove sua sessão. Para os demais testes e reversão, consulte [o bootstrap de acesso](../bootstrap/openshift-access/README.md). Preserve o acesso kubeadmin até validar também o novo administrador global.

### 10.5 Entrar como administrador do cluster e do Argo

Em uma nova janela privada do console OpenShift, escolha **keycloak** e entre como **openshift-admin** com sua senha atual. Confira o acesso à perspectiva administrativa e aos projetos do cluster.

Na sessão kubeadmin, confira os grupos e o vínculo:

```bash
oc get user openshift-admin
oc get group openshift-cluster-admins -o yaml
oc get clusterrolebinding keycloak-openshift-cluster-admins
```

No Argo, sincronize **argocd-cluster**. Saia da interface e escolha **Log in via OpenShift**; na tela do OpenShift, selecione **keycloak** e entre como **openshift-admin**. Confira o usuário e o grupo em **User Info** e teste a sincronização de uma aplicação autorizada.

Mantenha o `admin` local do Argo como recuperação. As contas `observability-admin` e de leitura não recebem administração do Argo por esse mapeamento.

## 11. Verificar a stack base

### 11.1 Reconciliação e recursos

```bash
oc -n openshift-gitops get applications.argoproj.io
oc -n metallb-system get jobs,ipaddresspools,l2advertisements
oc -n observability-apps get monitoringstack,pods,svc,pvc
oc -n pyroscope get statefulset,pods,svc,pvc
oc -n openshift-logging get pods,pvc,lokistack
oc -n tempo get tempomonolithic,pods,svc,pvc
oc -n observability get opentelemetrycollector,pods,svc
oc -n grafana get grafana,grafanadatasource,route
oc -n zabbix get pods,svc,route,pvc
```

Confira Applications habilitadas `Synced / Healthy`, PVCs `Bound`, workloads prontos e Jobs concluídos. Investigue pods em erro antes de seguir.

### 11.2 Conferir o MetalLB

```bash
oc get nodes -o wide
oc -n metallb-system get ipaddresspool lb-pool -o jsonpath='{.spec.addresses}'
oc -n metallb-system get job address-pool-configurator
```

Confira o Job concluído e a faixa `.200–.250` da rede do nó.

#### Testar IP LoadBalancer e conectividade — opcional

Execute somente para validar serviços LoadBalancer. Para continuar a instalação, avance para 11.3.

Crie o workload de verificação:

```bash
oc create namespace validacao-metallb
oc -n validacao-metallb create deployment web --image=registry.access.redhat.com/ubi9/httpd-24@sha256:f044268a321397ff4af4945763e558e14aad584c915e4cae9ae485a30deda303
oc -n validacao-metallb rollout status deployment/web --timeout=5m
oc -n validacao-metallb expose deployment web --port=8080 --target-port=8080 --type=LoadBalancer
oc -n validacao-metallb get service web
```

Aguarde um `EXTERNAL-IP` dentro da faixa do MetalLB. Informe o endereço para testar o acesso:

```bash
printf '%s' 'EXTERNAL-IP atribuído ao Service web: '
IFS= read -r METALLB_TEST_IP
curl --fail --show-error --connect-timeout 5 "http://$METALLB_TEST_IP:8080/"
```

Se o acesso falhar, confira anúncio e roteamento entre o host e a rede CRC.

Após a verificação, remova somente o namespace temporário:

```bash
oc delete namespace validacao-metallb
```

### 11.3 Telemetria e datasources

| Teste | Como executar | Resultado esperado |
|---|---|---|
| Métricas | Grafana Explore, datasource Prometheus Apps, query up; selecione o target avaliado | Série do target com valor 1 e amostra recente |
| Frescor | Para o target selecionado, consulte time() - timestamp(up) com os mesmos labels | Idade compatível com o intervalo de coleta; up=0 ou amostra antiga não é PASS |
| Logs | Gere uma requisição identificável na aplicação e consulte Loki pelo namespace/labels reais, no período correspondente | Mensagem recente do workload correto |
| Traces | Gere chamadas na aplicação instrumentada, considerando sampling; consulte Tempo por trace ID ou atributos do serviço | Trace recente com spans da chamada |
| Profiles | Gere atividade limitada na aplicação com agente Pyroscope e selecione sua aplicação/labels | Perfil recente e flamegraph com amostras |
| Zabbix | Consulte um item recente autorizado ao usuário técnico pelo datasource | Mesmo item/valor acessível pela API |
| Correlação | Abra os links trace → logs/métricas/profiles usando os identificadores e labels efetivos | Consulta aponta para a aplicação/período corretos |

Gere tráfego na aplicação instrumentada antes de consultar. Se não houver dados, confira coleta, permissões e sampling.

Use os datasources corretos para plataforma e aplicações. Para drilldowns, consulte o [guia do Grafana](https://github.com/thiagobotelho/grafana-gitops/blob/main/docs/DRILLDOWN.md).

### 11.4 Autenticação, autorização e persistência

Em janelas privadas separadas, teste Grafana OIDC, Zabbix SAML e console OpenShift: login permitido, papel recebido, logout e usuário sem permissão.

Para verificar persistência, crie dados descartáveis, reinicie um workload por vez e confira os dados após o rollout. Preserve os PVCs.

## 12. Network Observability opcional

Após estabilizar a stack base, prepare o bucket e o Secret do Loki dedicado:

```bash
oc whoami
oc -n openshift-logging rollout status deployment/minio --timeout=5m
oc create namespace netobserv --dry-run=client -o yaml | oc apply -f -
cd "$WORKDIR/network-observability-gitops"
bash scripts/bootstrap-netobserv-loki.sh
bash scripts/bootstrap-netobserv-loki.sh --check
```

O bootstrap usa o contexto atual e aceita somente o CRC. Se a autenticação
falhar, refaça o login no mesmo terminal. Não envie senhas ou tokens.

Confira a capacidade disponível e cadastre a Application:

```bash
cd "$WORKDIR/argocd-gitops"
oc kustomize optional
oc apply -k optional
oc -n openshift-gitops get application network-observability
oc get flowcollector cluster
oc -n netobserv get pods
oc adm top pods -n netobserv
```

Aguarde Operator e CRD antes do FlowCollector. Confira o recurso `Ready` e fluxos recentes na interface. Para sampling e retenção, consulte as [políticas](https://github.com/thiagobotelho/network-observability-gitops/blob/main/docs/POLITICAS.md).

### 12.1 Network Events experimental opcional

Somente para cluster descartável: TechPreviewNoUpgrade é irreversível e impede
atualizações menores. Não é requisito para os exercícios de NetworkPolicy.
Execute separadamente o [bootstrap OVNObservability](../bootstrap/ovn-observability/README.md),
aguarde os Operators/pools estabilizarem e selecione o perfil:

```bash
cd "$WORKDIR/argocd-gitops"
oc apply -k optional/network-events
oc -n openshift-gitops get application network-observability
```

No Console, use Observe → Network Traffic → Network Events. O diretório
optional padrão continua sem esse recurso. Reaplicá-lo desativa somente a
coleta experimental; não reverte a FeatureGate.

## 13. Service Mesh opcional, em uma única Application

### 13.1 Conferir catálogo e cadastrar a infraestrutura

```bash
oc -n openshift-marketplace get packagemanifest servicemeshoperator3
oc adm top nodes
cd "$WORKDIR/service-mesh-gitops"
oc kustomize overlays/desenvolvimento
cd "$WORKDIR/argocd-gitops"
oc apply -k optional/service-mesh
oc -n openshift-gitops get application service-mesh
```

A Application inicia o sync automaticamente e corrige divergências com self-heal. O prune automático fica desativado. O Argo gerencia somente a infraestrutura do mesh.

### 13.2 Acompanhar a instalação automática

A Subscription usa `installPlanApproval: Automatic`. A instalação e as atualizações no canal `stable-3.4` dispensam aprovação manual. `startingCSV` define a versão inicial, sem fixar atualizações futuras.

```bash
oc -n openshift-operators get subscription servicemeshoperator3
oc -n openshift-operators get installplan,csv
oc get istios,istiocnis,istiorevisions,istiorevisiontags
oc -n istio-system get pods
oc -n istio-cni get pods
```

Confira CSV `Succeeded`, CRDs `Established` e condições `Ready` de Istio/CNI. Se já existia um InstallPlan manual pendente, revise o plano indicado em `status.installPlanRef` da Subscription e aprove somente esse plano uma vez. Para diagnóstico, consulte a [instalação do mesh](https://github.com/thiagobotelho/service-mesh-gitops/blob/main/docs/INSTALACAO-CRC.md).

### Kiali opcional na mesma Application

Para habilitar o grafo e as métricas do mesh usando o Prometheus de aplicações existente:

```bash
cd "$WORKDIR/argocd-gitops"
oc apply -k optional/service-mesh-kiali
oc -n openshift-gitops get application service-mesh
oc -n istio-system get kiali,pods,route
oc -n istio-system get route kiali -o jsonpath='https://{.spec.host}{"\n"}'
```

Entre pelo OpenShift e selecione seu IdP. No Kiali, abra **Traffic Graph**, selecione `mesh-lab` e gere tráfego dos exercícios. Consulte o [guia do Kiali](https://github.com/thiagobotelho/service-mesh-gitops/blob/main/docs/KIALI.md). Este perfil substitui a fonte da mesma Application; não reaplique o perfil sem Kiali depois dele.

### 13.3 Aplicar exercícios manualmente, um cenário por vez

```bash
cd "$WORKDIR/mesh-apps-lab"
oc kustomize scenarios/01-baseline
oc apply -k scenarios/01-baseline
oc -n mesh-lab rollout status deployment/httpbin --timeout=5m
oc -n mesh-lab rollout status deployment/sleep --timeout=5m
oc -n mesh-lab rollout status deployment/sleep-denied --timeout=5m
```

Avance um cenário por vez conforme os [exercícios](https://github.com/thiagobotelho/mesh-apps-lab/blob/main/docs/EXERCICIOS.md). Siga a [transição manual](https://github.com/thiagobotelho/mesh-apps-lab/blob/main/docs/APLICACAO-MANUAL.md) para remover recursos exclusivos da fase anterior.

Mantenha as APIs de exercício fora do Argo. Use somente a Application `service-mesh` para a infraestrutura.

## 14. Reexecução, diagnóstico e critérios de aceite

### 14.1 O que pode ser repetido e o que exige revisão

| Ação | Cuidado |
|---|---|
| oc get, describe e renderização | Leitura; revise a saída antes de compartilhar |
| oc apply em manifest versionado | Pode criar/alterar recursos; confira contexto e diff |
| Refresh do Argo | Recalcula comparação; não força uma operação de sync |
| Sync do Argo | Aplica o desejado e pode executar hooks; confira prune e credenciais |
| Gerar senha e criar Secret | Somente primeira instalação; não é rotação idempotente |
| Reimportar realm | Pode alterar objetos de identidade; confira usuários, clients e comportamento de importação |
| Reiniciar workload | Pode interromper sessões; aguarde readiness e teste novamente |
| Excluir Application | Confira finalizers; pode remover os recursos gerenciados |
| crc delete | Remove cluster e dados da VM; exige decisão explícita e backup quando necessário |

Para repetir uma operação que falhou, corrija a causa e execute **Sync**. Preserve Applications, PVCs e contas existentes.

### 14.2 Registrar os resultados

| Etapa | Evidência mínima | Quando marcar PASS |
|---|---|---|
| Plataforma | Versões, operadores, nó e StorageClass | Recursos esperados estáveis |
| GitOps | Application, revisão sincronizada e operação | Synced/Healthy sem erro de geração ou sync |
| MetalLB | Pool, Job, Service e teste de acesso | Cada comportamento efetivamente observado |
| Identidade | Login novo, usuário/role e caso sem autorização | Resultado esperado em cada serviço |
| Telemetria | Query, janela temporal e dado recente | Dado produzido e recuperado no backend correto |
| Persistência | Dado descartável antes/depois do reinício | Dado preservado sem intervenção oculta |
| Mesh | Fase, identidade, chamada e resultado | Casos permitidos e negados conforme política |
| Reexecução | Diff e estado antes/depois | Sem rotação indevida ou perda de dados |

Registre resultados e evidências fora dos repositórios: `PASS`, `FAIL`, `BLOCKED` ou `NOT RUN`. Omita credenciais e dados sensíveis. Marque `PASS` somente após executar a verificação correspondente.

## Referências

- [CRC: uso](https://crc.dev/docs/using/) e [diagnóstico](https://crc.dev/docs/troubleshooting/).
- [Certificados do ingress OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_and_compliance/certificate-types-and-descriptions); consulte a versão correspondente ao seu bundle.
- [Endpoints OIDC do Keycloak](https://www.keycloak.org/securing-apps/oidc-layers).
- [Primeiro login Zabbix](https://www.zabbix.com/documentation/7.4/en/manual/quickstart/login) e [SAML](https://www.zabbix.com/documentation/7.4/en/manual/web_interface/frontend_sections/users/authentication/saml).
- [Operação desta stack](OPERACAO.md) e [autenticação OpenShift/Keycloak](AUTENTICACAO-KEYCLOAK-CRC.md).

Shells: [Bash](https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html) e [Zsh](https://zsh.sourceforge.io/Doc/Release/Shell-Builtin-Commands.html#index-read).

## Observabilidade opcional do mesh

Depois de estabilizar os backends, selecione o perfil completo conforme [arquitetura e integrações](ARQUITETURA-E-INTEGRACOES.md). Consulte o guia operacional do componente para tracing, consultas e alertas; os exercícios permanecem em mesh-apps-lab.

## PKI externa opcional

Depois dos componentes básicos, siga [optional/pki](../optional/pki/README.md) para instalar Vault e cert-manager, fazer o bootstrap e adicionar o mesh isolado. Não substitua a CA do mesh ativo reaplicando um perfil de laboratório.
