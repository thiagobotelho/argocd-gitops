# Tutorial CRC/OpenShift Local da stack GitOps

## 1. Objetivo e forma de execução

Este guia instala e valida a stack em um CRC pessoal novo, explicando cada ação. Execute os blocos em ordem e cada comando separadamente, conferindo seu retorno, em **Bash ou Zsh**. Não há scripts Python embutidos nem loops de instalação. Os comandos de preparação são explícitos; na etapa 9, um script versionado e revisável automatiza certificado e IdP SAML. As interfaces administrativas continuam disponíveis para conferência e testes de identidade.

O Argo CD continua responsável por reconciliar os manifests dos componentes. Isso é parte da arquitetura GitOps: os comandos manuais preparam suas dependências, cadastram as Applications e verificam o resultado.

**Antes de avançar:** pare se o resultado esperado não ocorrer. Não cole o documento inteiro no terminal. Os comandos de criação de Secret são destinados à primeira instalação: se o Secret já existe, preserve seu valor e investigue antes de continuar. Reaplicar uma senha recém-gerada pode quebrar o acesso a um banco que já possui dados.

| Componente | Objetivo |
|---|---|
| OpenShift GitOps/Argo CD | Reconciliar configuração declarativa e mostrar diferenças |
| MetalLB | Atribuir e anunciar endereços para Services LoadBalancer |
| Prometheus Apps | Coletar métricas das aplicações com MonitoringStack |
| Loki/MinIO | Armazenar logs e objetos usados pelo Loki |
| TempoMonolithic | Armazenar traces no perfil local |
| OpenTelemetry Collector | Receber e encaminhar telemetria |
| Pyroscope | Armazenar profiles das aplicações instrumentadas |
| Keycloak | Fornecer identidade OIDC/SAML, usuários e grupos |
| Grafana | Consultar métricas, logs, traces, profiles e Zabbix |
| Zabbix | Monitoramento e autenticação SAML/JIT |
| Network Observability | Opcional: fluxos de rede coletados com eBPF |
| Service Mesh | Opcional: CNI, plano de controle, mTLS e autorização L7 |

## 2. Preparar o host e as fontes

### 2.1 Ferramentas e capacidade

**Objetivo:** confirmar as ferramentas antes de alterar o ambiente.

```bash
printf 'Bash: %s | Zsh: %s\n' "${BASH_VERSION:-não ativo}" "${ZSH_VERSION:-não ativo}"
git --version
crc version
openssl version
curl --version
```

**Esperado:** ferramentas disponíveis. O oc será disponibilizado pelo próprio CRC depois do start. O perfil recomendado pelo projeto para a stack completa é 10 vCPUs, 40 GiB de RAM e disco de 200 GiB para a VM; reserve recursos adicionais para o host. Isso não é o mínimo oficial do CRC nem garantia de capacidade para qualquer carga.

Execute crc no host que administra a VM, sem sudo crc. Se ela pertence ao Windows, faça seu ciclo de vida nesse host; configure posteriormente o acesso a partir do WSL. Ter oc no WSL não significa ter uma segunda VM CRC.

Os blocos usam a sintaxe comum aos dois shells. Não é necessário abrir outro shell. Use o mesmo terminal para ler uma variável e criar o Secret que a consome; abrir bash ou zsh depois da leitura não transfere automaticamente essas variáveis.

Nos prompts, o texto mostrado é apenas a pergunta: digite a senha quando a leitura aguardar. Não substitua a pergunta pela própria senha. A senha digitada com read -s não aparece no terminal. Não cole outros comandos enquanto o prompt estiver aguardando.

O formato usado em todo o guia é printf para exibir a pergunta, seguido de IFS= read -r -s VARIAVEL para leitura silenciosa. IFS= preserva espaços e -r preserva barras invertidas. Não use read -p nesses blocos: no Bash é opção de prompt; no Zsh refere-se a coprocessos. Para endereços e nomes de recursos, a leitura usa read -r, sem -s, para permitir conferir o texto.

### 2.2 Escolher um diretório novo

**Objetivo:** trabalhar sem sobrescrever checkouts, credenciais ou alterações anteriores.

```bash
export WORKDIR="$HOME/labs/openshift-local-stack"
mkdir -p "$WORKDIR"
cd "$WORKDIR"
```

Se esse diretório já contiver projetos, escolha outro nome. A variável WORKDIR é apenas o caminho da sua estação e será usada nos próximos comandos.

### 2.3 Clonar cada repositório

**Objetivo:** obter fontes revisáveis na branch main, incluindo os módulos opcionais.

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

**Esperado:** cada clone termina sem erro. Para um repositório privado, configure autenticação Git na estação sem embutir tokens na URL. Essa credencial não é automaticamente transferida ao Argo CD. Em forks, ajuste também os repoURL das Applications; mudar somente os clones não muda as fontes do cluster.

Confira as referências dos projetos antes de instalar:

```bash
git -C "$WORKDIR/argocd-gitops" log -1 --oneline
git -C "$WORKDIR/metallb-gitops" log -1 --oneline
git -C "$WORKDIR/keycloak-gitops" log -1 --oneline
```

Registre os SHAs dos demais projetos ao validar cada componente. As Applications seguem main; alterações posteriores podem mudar a referência reconciliada. Para um ensaio com referências congeladas, planeje explicitamente o pin de todas as fontes envolvidas.

## 3. Criar o CRC

### 3.1 Decidir se haverá exclusão

**Objetivo:** distinguir instalação nova de reinicialização. Se não existe cluster, pule os dois comandos de exclusão. Se existe e deseja reconstruí-lo, faça backup dos dados que precisa preservar antes de executar:

```bash
crc stop
crc delete
```

**Efeito:** perde-se o conteúdo do cluster e dos volumes da VM. Manifests Git não recuperam bancos, usuários alterados pela UI, logs ou dashboards não versionados. Não exporte todos os Secrets para um arquivo desprotegido. Para comparar uma reconstrução, prefira inicialmente a mesma versão de CRC/bundle; avalie upgrades separadamente.

### 3.2 Definir o perfil e iniciar

**Objetivo:** disponibilizar CPU, memória, disco e monitoramento de plataforma.

```bash
crc config set preset openshift
crc config set cpus 10
crc config set memory 40960
crc config set disk-size 200
crc config set enable-cluster-monitoring true
crc setup
crc start
```

Forneça o pull secret Red Hat pelo mecanismo solicitado pelo CRC; não o coloque no Git. Espere o start terminar. O setup prepara o host; start cria/inicia a VM. Não use crc cleanup de rotina: ele também reverte configurações de host, incluindo DNS. Veja [uso do CRC](https://crc.dev/docs/using/) e [diagnóstico do CRC](https://crc.dev/docs/troubleshooting/).

### 3.3 Autenticar e isolar o kubeconfig

**Objetivo:** garantir que os próximos comandos apontem somente para este laboratório.

```bash
umask 077
export KUBECONFIG="$WORKDIR/kubeconfig-crc"
eval "$(crc oc-env)"
oc login -u kubeadmin https://api.crc.testing:6443
oc whoami
oc whoami --show-server
oc get nodes
```

Digite a senha no prompt. Para consultar a senha do `kubeadmin`, execute **no host que administra a VM CRC**, em terminal privado:

```bash
crc console --credentials
```

**Objetivo:** mostrar as credenciais locais do CRC; a saída contém senhas e não deve ser compartilhada. Se o CRC está no Windows, execute o comando no Windows; depois use a senha no prompt do `oc login` no WSL. Não passe a senha em `--password` nem a coloque no histórico.

O `kubeadmin` é usado aqui para administração do OpenShift pelo terminal. A interface do Argo CD usará seu usuário local `admin`, descrito na etapa 5.3. O kubeconfig contém credenciais: mantenha-o fora dos repositórios e de anexos. Em outro terminal, reconfigure WORKDIR e KUBECONFIG antes de usar oc.

**Esperado:** servidor do CRC, identidade administrativa e nó Ready. Não prossiga se aparecer outro cluster.

### 3.4 Verificar a plataforma e o armazenamento

```bash
oc get clusterversion
oc get clusteroperators
oc get storageclass
oc -n openshift-monitoring get pods
```

**Objetivo:** resolver falhas de plataforma antes de instalar aplicações. Aguarde os operadores esperados estabilizarem; investigue Degraded=True persistente. Componentes opcionais desativados pelo perfil não devem ser confundidos com falhas de instalação.

**Esperado:** armazenamento funcional, inclusive crc-csi-hostpath-provisioner, usado pelos overlays CRC de Loki/Network Observability. Se o bundle disponibiliza outra classe, adapte os overlays antes do sync. O cluster monitoring deve estabilizar. User Workload Monitoring permanece desativado no perfil: esta stack usa Prometheus Apps para workloads, além do monitoramento nativo da plataforma.

## 4. Preparar namespaces e Secrets iniciais

### 4.1 Criar os namespaces necessários ao bootstrap

**Objetivo:** permitir criar as credenciais antes de iniciar os consumidores.

```bash
oc create namespace openshift-logging
oc create namespace keycloak-dev
oc create namespace zabbix
oc create namespace grafana
```

**Esperado:** namespaces criados. AlreadyExists não exige excluir o namespace; confirme que pertence ao laboratório esperado. Os demais namespaces serão criados pelos manifests. Os comandos seguintes são individuais: não há execução automática em lote.

### 4.2 MinIO e acesso S3 do Loki

**Objetivo:** criar a credencial do servidor MinIO e a mesma credencial para seu cliente Loki.

Confira primeiro se já existem:

```bash
oc -n openshift-logging get secret minio-credentials --ignore-not-found
oc -n openshift-logging get secret loki-s3 --ignore-not-found
```

**Para cluster novo:** ambos devem estar ausentes. Se algum existir, pare e verifique seu uso; não gere uma senha nova para sobrescrevê-lo.

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

**Como ler os comandos:** openssl gera a senha em memória; printf envia seus bytes; a substituição de processo disponível em Bash e Zsh `<(...)` fornece um descritor ao oc, sem colocar a senha no argumento do processo ou em arquivo persistente. As chaves públicas usam from-literal. Não ative set -x. O segundo Secret deve usar a mesma senha do primeiro. Execute cada comando separadamente e confira seu retorno. Se uma criação falhar, não execute unset nem avance antes de corrigir a causa.

```bash
oc -n openshift-logging describe secret minio-credentials
oc -n openshift-logging describe secret loki-s3
```

**Esperado:** chaves com tamanho não zero, sem imprimir os valores. Criar um Secret não verifica conexão ao MinIO; essa prova ocorre depois do deploy.

### 4.3 Banco do Keycloak

**Objetivo:** compartilhar usuário, senha e nome de banco entre PostgreSQL e Keycloak.

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

**Esperado:** username, password e database presentes. Não altere apenas o Secret de uma instalação existente: a senha dentro do banco também precisa ser coordenada.

### 4.4 Senhas iniciais dos usuários do realm

**Objetivo:** fornecer ao Job declarativo do Keycloak as senhas iniciais de três usuários. Escolha senhas distintas e guarde-as em seu gerenciador de senhas; a leitura é silenciosa.

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

Cada test verifica apenas se a variável tem conteúdo e não imprime a senha. Se algum falhar, não execute a criação: leia novamente a senha correspondente. Para receber uma confirmação visível sem revelar os valores:

```bash
test -n "$GRAFANA_ADMIN_PASSWORD" && printf 'Grafana: preenchida\n'
test -n "$ZABBIX_ADMIN_PASSWORD" && printf 'Zabbix: preenchida\n'
test -n "$OBSERVABILITY_ADMIN_PASSWORD" && printf 'Observability: preenchida\n'
```

**Esperado:** as três confirmações aparecem. Caso contrário, pare antes de criar o Secret.

```bash
oc -n keycloak-dev create secret generic keycloak-observability-users \
  --from-file=GRAFANA_ADMIN_PASSWORD=<(printf '%s' "$GRAFANA_ADMIN_PASSWORD") \
  --from-file=ZABBIX_ADMIN_PASSWORD=<(printf '%s' "$ZABBIX_ADMIN_PASSWORD") \
  --from-file=OBSERVABILITY_ADMIN_PASSWORD=<(printf '%s' "$OBSERVABILITY_ADMIN_PASSWORD")
unset GRAFANA_ADMIN_PASSWORD ZABBIX_ADMIN_PASSWORD OBSERVABILITY_ADMIN_PASSWORD
oc -n keycloak-dev describe secret keycloak-observability-users
```

O Secret não cria usuários sozinho. O Job keycloak-config-cli-observability importará o realm observability, usuários, grupos e clients a partir do repositório Keycloak. A senha inicial armazenada não comprova a senha atual depois de uma alteração pela UI. Esses usuários são diferentes do administrador inicial do realm master e do administrador local do Zabbix.

### 4.5 Banco do Zabbix

**Objetivo:** compartilhar a credencial PostgreSQL entre banco, servidor e frontend.

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

**Objetivo:** entender por que não há uma entrada manual nesta etapa. O overlay desenvolvimento do metallb-gitops recebe status.hostIP pelo Downward API e calcula a faixa .200-.250 a partir dos três primeiros octetos do IPv4 do nó. Basta o App-of-Apps; não crie metallb-pool-input para o CRC.

Essa convenção é específica da rede local de laboratório; não descobre máscara nem reserva DHCP/IPAM. Aceite e produção mantêm configuração explícita. A atribuição de IP e a conectividade serão verificadas separadamente.

## 5. Instalar OpenShift GitOps manualmente em fases

### 5.1 Conferir os manifests e instalar o Operator

**Objetivo:** criar os namespaces e o recurso de instalação antes da instância ArgoCD.

```bash
cd "$WORKDIR/argocd-gitops"
cat base/subscription.yaml
oc apply -f base/namespace.yaml
oc apply -f base/operatorgroup.yaml
oc apply -f base/subscription.yaml
oc -n openshift-gitops-operator get subscription,installplan,csv
```

O namespace do Operator é openshift-gitops-operator; o da instância é openshift-gitops. O canal declarado é latest, com aprovação Automatic: isso não fixa uma versão. Confira o catálogo compatível com seu bundle e registre o CSV efetivamente instalado. Não troque canal durante a validação sem revisar a compatibilidade.

**Esperado:** a Subscription aponta para um installedCSV, e o CSV termina em Succeeded. Repita a consulta enquanto instala. Para falhas, examine Subscription, InstallPlan e eventos desse namespace.

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

**Objetivo:** evitar criar uma ArgoCD CR antes de a API reconhecer seu tipo. O ClusterRoleBinding concede cluster-admin ao application controller para o bootstrap do laboratório; AppProject não substitui essa permissão Kubernetes. Não transporte esse desenho para ambiente compartilhado sem revisão de RBAC.

Quando o deployment existir:

```bash
oc -n openshift-gitops wait --for=condition=Available deployment/openshift-gitops-server --timeout=10m
oc -n openshift-gitops get pods,route
```

**Esperado:** servidor disponível e Route criada. Não use oc apply -k overlays/cluster como primeira chamada de um cluster vazio, pois mistura fases que dependem da CRD.

### 5.3 Consultar o acesso administrativo local do Argo CD

**Objetivo:** entrar na interface com o usuário local `admin`, sem conceder permissões extras ao `kubeadmin` no RBAC do Argo.

Consulte o endereço:

```bash
oc -n openshift-gitops get route openshift-gitops-server \
  -o jsonpath='{.spec.host}{"\n"}'
```

Abra o endereço com `https://`. Para obter a senha do usuário **admin**, execute somente no seu terminal privado:

```bash
oc -n openshift-gitops get secret openshift-gitops-cluster \
  -o jsonpath='{.data.admin\.password}' | base64 --decode
printf '\n'
```

**Esperado:** o valor local da chave `admin.password`. A saída contém a senha: não cole no chat, em relatórios, em capturas ou no Git. Não execute com gravação de terminal ou `set -x` habilitado.

Na página do Argo, use o formulário de usuário e senha: **Username = admin**, **Password = valor consultado**. Não escolha o botão de login pelo OpenShift para esse procedimento. Depois do login, confira o usuário em **User Info**.

O Secret depende do nome da instância; neste repositório a ArgoCD CR chama-se `openshift-gitops`. Se a senha já foi alterada pela interface, use a credencial atual: não suponha que o Secret ainda corresponda à senha em uso. Se o administrador local estiver desabilitado por uma configuração personalizada, revise essa decisão em vez de alterar RBAC de outros usuários como atalho.

As credenciais do Argo são diferentes das do OpenShift e do Keycloak. O RBAC SSO continua com `role:readonly` como padrão e somente os grupos administrativos explicitamente configurados. Não é necessário acrescentar uma regra para o `kubeadmin` para seguir este tutorial.

### 5.4 Validar o acesso às fontes Git e imagens

**Objetivo:** resolver autenticação antes de culpar Kustomize ou o Operator.

Com a sessão local `admin` do Argo, abra **Settings > Repositories**, cadastre cada fonte privada exigida pelas Applications e confirme conexão bem-sucedida. Use credencial nova de leitura restrita aos projetos; não coloque token no repoURL ou no Git. Fontes públicas acessíveis não exigem credencial privada.

Confira também as imagens referenciadas nos overlays. Se alguma imagem for privada, crie o pull secret no namespace consumidor e vincule-o à ServiceAccount correspondente antes de iniciar o workload. Credenciais Git não autenticam pulls no Quay. ImagePullBackOff exige conferir a imagem, sua existência e a autenticação; não trocar a tag às cegas.

Referência: [acesso à instância padrão do OpenShift GitOps](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/1.20/html/installing_gitops/installing-openshift-gitops).

## 6. Iniciar a stack base pelo App-of-Apps

### 6.1 Renderizar antes de aplicar

**Objetivo:** conferir o objeto raiz e as aplicações que ele criará.

```bash
cd "$WORKDIR/argocd-gitops"
oc kustomize overlays/desenvolvimento
oc kustomize overlays/applications/desenvolvimento
```

**Esperado:** Application platform-apps na primeira saída; Applications dos componentes base na segunda. Confira repoURL, targetRevision, path e destination. Network Observability e Service Mesh são opcionais e ainda não entram aqui.

### 6.2 Aplicar e acompanhar

```bash
oc apply -k overlays/desenvolvimento
oc -n openshift-gitops get applications.argoproj.io
```

**Objetivo:** entregar ao Argo o controle dos recursos versionados. O App-of-Apps e as aplicações base usam autosync, prune e selfHeal: alterações no Git podem criar, corrigir e remover recursos declarados. Não altere deployments gerenciados como correção permanente fora do Git.

**Esperado:** surgem os componentes base e suas operações de sincronização. Repita a consulta durante a instalação. Instalação de Operator, criação de CRD e readiness são fases diferentes; sync waves não garantem que toda dependência funcional esteja pronta. Grafana pode aguardar grafana-oauth; isso será resolvido na etapa 8 e não deve ser registrado como PASS enquanto faltar.

### 6.3 Diagnosticar uma falha sem ocultá-la

Exemplo para Grafana:

```bash
oc -n openshift-gitops get application grafana -o jsonpath='{.status.conditions}'
oc -n openshift-gitops get application grafana -o jsonpath='{.status.operationState.message}'
oc -n grafana get pods,pvc,events
```

**Objetivo:** distinguir credencial ausente, erro Git, CRD inexistente, falta de recurso e falha do container. Substitua grafana pelo app/namespace que está investigando. Não use redirecionamento de erros seguido de true para fazer a etapa parecer concluída. Para erro no matches for kind GrafanaDashboard/GrafanaFolder em instalação nova, confira as CRDs e a instalação do Operator:

```bash
oc get crd grafanas.grafana.integreatly.org grafanafolders.grafana.integreatly.org grafanadashboards.grafana.integreatly.org
oc -n grafana-operator get subscription,installplan,csv,pods
```

As CRs devem vir depois da Subscription: o perfil usa Operator na wave 2, instância na 10, pastas na 35 e dashboards na 40. SkipDryRunOnMissingResource não cria a CRD nem torna segura uma ordem invertida. Confira a revisão do repositório e corrija a ordem no Git; depois atualize o diff e dispare novo Sync no Argo quando a operação anterior falhou. Uma CRD já presente deve ter condição Established antes de depender dela.


### 6.4 Acompanhar as imagens automáticas do MinIO e do cliente mc

**Objetivo:** conferir a produção das imagens usadas pelo overlay CRC. A sincronização completa de `loki` executa o hook `crc-minio-images`: ele inicia primeiro o build do servidor e depois o do cliente, aguardando as duas imagens antes de liberar o MinIO. Não há comando manual de build nesta etapa.

Confira o registro integrado, as BuildConfigs e o andamento:

```bash
oc get clusteroperator image-registry
oc -n openshift-image-registry get pods
oc -n openshift-logging get buildconfig,build,imagestream
oc -n openshift-logging get job crc-minio-images
oc -n openshift-logging logs job/crc-minio-images
```

**Esperado:** registro disponível e hook em execução ou concluído. Na primeira instalação surgem os builds `minio-crc` e `mc-crc`. Tags já publicadas são reutilizadas; um build ativo é acompanhado sem iniciar uma duplicata. O hook atende tanto BuildConfigs novas quanto as já existentes.

Após o hook concluir, confira as tags publicadas:

```bash
oc -n openshift-logging get imagestreamtag minio-crc:RELEASE.2025-09-07T16-13-09Z
oc -n openshift-logging get imagestreamtag mc-crc:RELEASE.2025-08-13T08-35-41Z
```

**Esperado:** ambas existem. Acompanhe então a aplicação e o bucket:

```bash
oc -n openshift-logging rollout status deployment/minio --timeout=10m
oc -n openshift-logging get jobs,pods
```

**Esperado:** MinIO pronto e Job de bucket concluído; o sync pode avançar para o LokiStack. O hook tem prazo global de 35 minutos e interrompe em caso de falha. Consulte seus logs, os eventos e os logs do build pelo nome exibido em `get builds` antes de tentar novamente.

Se `loki` já esgotou as tentativas, faça **Refresh** para carregar a revisão e depois **Sync completo** no Argo CD. Refresh isolado não dispara o hook; sync seletivo de recursos também não o executa. Após corrigir a causa de uma falha, um novo Sync substitui o hook anterior, acompanha builds ativos e reutiliza imagens publicadas. Preserve o PVC `minio-data`.

A automação é exclusiva do overlay de desenvolvimento e depende de waves/hooks do Argo; `oc apply -k` isolado não reproduz essa ordem. Uma tag existente não é reconstruída automaticamente. Consulte [o funcionamento e a atualização das imagens](https://github.com/thiagobotelho/loki-gitops#imagens-automáticas-no-crc).

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

**Objetivo:** comprovar que o servidor e a importação de identidade terminaram. Na UI do Keycloak, entre com o administrador inicial informado pelo Secret keycloak-dev-initial-admin. Consulte apenas username e password necessários na interface local de Secrets do OpenShift; não exporte o objeto inteiro ou inclua os valores em evidências.

**Esperado:** realm observability, usuários grafana-admin, zabbix-admin e observability-admin; clients grafana, zabbix e openshift. Confira também os grupos de cada usuário. Um Job Complete não substitui a conferência da configuração importada.

### 7.2 Consultar o administrador inicial do Keycloak

**Objetivo:** acessar o console administrativo do Keycloak para configurar clients, certificados e usuários do realm `observability`.

Consulte o endereço público:

```bash
oc -n keycloak-dev get route keycloak -o jsonpath='{.spec.host}{"\n"}'
```

Abra `https://<host-da-route>/admin/`. O operador gera o Secret inicial com o nome da Keycloak CR seguido de `-initial-admin`. Neste repositório: **keycloak-dev-initial-admin**, no namespace **keycloak-dev**.

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

**Esperado:** as duas credenciais de bootstrap. Não presuma que o nome seja `admin`: use o valor de `username`. A saída da segunda consulta contém a senha; não a publique nem a salve em relatório.

Entre no console administrativo e selecione o realm **observability** para as próximas etapas. A conta administrativa inicial pertence ao realm **master** e é diferente dos usuários `grafana-admin`, `zabbix-admin` e `observability-admin`.

A conta inicial é de bootstrap e pode ser temporária conforme a versão. Se já foi removida ou sua senha mudou, use o administrador permanente existente. Não recrie usuários, apague o banco ou reaplique Secrets para tentar restaurar a senha. Configure um administrador permanente para operação e siga o procedimento oficial de recuperação quando necessário.

Referências: [acesso inicial pelo Operator](https://www.keycloak.org/operator/basic-deployment) e [contas de bootstrap e recuperação](https://www.keycloak.org/server/bootstrap-admin-recovery).

### 7.3 Obter a CA do ingress deste CRC

**Objetivo:** consultar HTTPS validando a cadeia e o hostname, sem curl -k.

Para o certificado de ingress padrão do CRC:

```bash
mkdir -p "$WORKDIR/certificados"
oc -n openshift-ingress-operator get secret router-ca -o jsonpath='{.data.tls\.crt}' \
  | base64 --decode > "$WORKDIR/certificados/ingress-ca.crt"
openssl x509 -in "$WORKDIR/certificados/ingress-ca.crt" -noout -subject -issuer -dates
KEYCLOAK_URL="https://$(oc -n keycloak-dev get route keycloak -o jsonpath='{.spec.host}')"
curl --fail --show-error --cacert "$WORKDIR/certificados/ingress-ca.crt" \
  "$KEYCLOAK_URL/realms/observability/.well-known/openid-configuration"
```

Somente o certificado público tls.crt é extraído; nunca extraia tls.key. Com certificado de Route/ingress customizado, obtenha a cadeia correspondente em vez de assumir router-ca. O arquivo de CA público pode permanecer no diretório de trabalho, fora do Git.

**Esperado:** documento OIDC com issuer igual a KEYCLOAK_URL/realms/observability, sem erro TLS. Essa CA é do HTTPS, diferente do certificado que assina assertions SAML. Não reutilize automaticamente uma CA embutida em um bootstrap antigo.

## 8. Configurar Grafana OIDC manualmente

### 8.1 Conferir o client e transferir sua credencial

**Objetivo:** fazer Grafana e Keycloak usarem o mesmo client secret.

Na UI do Keycloak, selecione observability > Clients > grafana. Confira client authentication habilitada, Standard Flow e callback correspondente à URL pública do Grafana seguida de /login/generic_oauth. Use a URL da Route, sem inventar outro hostname:

```bash
oc -n grafana get route grafana-route
```

Abra Credentials no client grafana. Copie seu secret atual e informe-o no prompt local:

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

Se já existe, confira a procedência antes de atualizar; rotação exige coordenar os dois lados. Não regenere o client secret para contornar um erro de callback ou grupo.

### 8.2 Sincronizar e testar

No Argo, abra grafana, confira o diff e selecione Sync após criar o Secret. Refresh recalcula o estado desejado; não é uma nova operação de sync. Se o retry anterior esgotou, use Sync explicitamente. Aguarde:

```bash
oc -n grafana get grafana,pods,route
oc -n openshift-gitops get application grafana
```

**Esperado nesta etapa:** pods do Grafana prontos e login Keycloak funcionando em janela privada. O datasource Zabbix ainda depende da etapa 9.3; registre essa pendência e conclua esse bootstrap antes de exigir Synced/Healthy global. Não marque a stack inteira como PASS neste ponto. Teste grafana-admin com a senha escolhida na etapa 4.4. Confira o papel recebido; os grupos do Grafana usam os caminhos configurados no realm e não devem ser alterados para imitar os grupos SAML.

O Job PostSync grafana-enable-zabbix-app-plugin já está declarado no overlay; confira sua conclusão na UI do Argo depois de completar as dependências da etapa 9.3. No Grafana, veja o plugin Zabbix instalado e habilitado. Não substitua esse teste por apenas abrir um dashboard.

## 9. Configurar Zabbix SAML/JIT

### 9.1 Preparar o bootstrap automático de certificado e IdP

**Objetivo:** reaproveitar `zabbix-gitops/scripts/bootstrap-zabbix.sh` para obter o certificado público correto do Keycloak, publicar `zabbix-saml-idp` e cadastrar/reconciliar o IdP/JIT pela API Zabbix. Não é necessário exportar o certificado pela UI nem repetir o cadastro manual do IdP.

Atualize a cópia do repositório, preservando alterações locais:

```bash
cd "$WORKDIR/zabbix-gitops"
git status --short
git pull --ff-only
```

Se houver alterações locais ou o pull falhar, resolva antes de executar. Confira as dependências e o código que será utilizado:

```bash
bash --version
python3 --version
curl --version
jq --version
openssl version
oc whoami
oc whoami --show-server
less scripts/bootstrap-zabbix.sh
less scripts/extract-saml-signing-cert.py
oc -n zabbix get pods,route
oc -n keycloak-dev get pods,route
openssl x509 -in "$WORKDIR/certificados/ingress-ca.crt" -noout -subject -issuer -dates
```

**Esperado:** workloads prontos, contexto do CRC e CA HTTPS conferida na etapa 7.3. Python 3 usa somente biblioteca padrão para interpretar o XML; não há bloco Python para colar no terminal. O script é Bash e será chamado com `bash`, mesmo quando seu terminal for Zsh.

Informe a senha atual do administrador **local do Zabbix**, normalmente `Admin`. Essa conta é diferente de `zabbix-admin` no Keycloak. Em uma instalação nova, consulte a [documentação do primeiro login](https://www.zabbix.com/documentation/7.4/en/manual/quickstart/login) e altere a senha inicial pela UI antes de automatizar. A senha do PostgreSQL não serve para esse acesso.

```bash
printf '%s' 'Senha atual do administrador local Admin do Zabbix: '
IFS= read -r -s ZABBIX_ADMIN_PASSWORD
printf '\n'
test -n "$ZABBIX_ADMIN_PASSWORD"
```

Se o teste passou, configure o escopo:

```bash
export ZABBIX_ADMIN_PASSWORD
export BOOTSTRAP_CA_FILE="$WORKDIR/certificados/ingress-ca.crt"
export ZABBIX_ENABLE_SAML=true
export ZABBIX_ENABLE_SAML_JIT=true
export ZABBIX_MANAGE_SAML_IDP_CERT=true
export ZABBIX_MANAGE_GRAFANA_DATASOURCE=false
export ZABBIX_ENABLE_SAML_SCIM=false
```

**Motivo das opções:** a senha fica no ambiente do processo; a CA valida o HTTPS de Keycloak e Zabbix; certificado e IdP serão reconciliados; a conta técnica do Grafana continua na etapa 9.3; SCIM fica desabilitado. Não use `set -x` nem grave a senha em `.env`. Variáveis fornecidas no ambiente têm precedência sobre `.env` existente. Se o administrador local tiver outro nome, informe `ZABBIX_ADMIN_USER` explicitamente.

O script descobre URLs pelas Routes. Revise eventuais URLs e opções de um `.env` antigo antes de executá-lo. O client `zabbix` e seus mappers devem existir no realm `observability`; o script não os cria no Keycloak.

### 9.2 Executar e conferir certificado, IdP e JIT

Execute o código versionado:

```bash
bash scripts/bootstrap-zabbix.sh
```

**Efeitos:** autentica na API, verifica o diretório SAML existente, consulta o metadata por HTTPS validado, seleciona o certificado RSA publicado como assinatura, atualiza o ConfigMap quando necessário e aguarda o rollout do frontend. Depois cria/reconcilia IdP, grupos e mapeamentos JIT e habilita SAML. Pode interromper sessões durante o rollout; mantenha acesso administrativo local. Não é uma transação única: em caso de falha, investigue a etapa antes de repetir.

**Esperado:** mensagens de reconciliação SAML concluída, sem senha ou token na saída. Se o certificado for ambíguo, o EntityID divergir ou houver outro diretório SAML, o script interrompe para revisão. Em rotação, consulte a [seleção por fingerprint](https://github.com/thiagobotelho/zabbix-gitops#seleção-e-rotação-do-certificado-saml). Não contorne falhas TLS desabilitando a validação.

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

Na UI Zabbix, use o administrador local para **conferir**, sem cadastrar um segundo IdP, em Users > Authentication > SAML:

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

Esses mapeamentos concedem os papéis indicados; revise antes de executar em outro ambiente. A reconciliação pode substituir mapeamentos personalizados do diretório. No Keycloak, confira o ACS do client `zabbix`: URL pública do Zabbix seguida de `/index_sso.php?acs`; o mapper `groups` emite nomes sem caminho completo.

**Validação funcional:** teste `zabbix-admin` em janela privada, confira grupo/role, logout e um usuário sem mapeamento. JIT pode criar usuários no login; a conclusão do script não comprova autenticação SAML nem consulta de dados. Preserve o administrador local para recuperação.

### 9.3 Criar o usuário técnico do datasource

**Objetivo:** permitir ao Grafana consultar a API sem usar um administrador humano.

Na UI Zabbix, crie grafana-datasource com senha própria, grupo Grafana datasource readers e User role. Confira que o grupo permite autenticação interna para essa conta e que a role permite as operações de leitura da API necessárias ao plugin. Não a torne dependente de um login SAML interativo.

Em Host permissions do grupo, conceda Read somente aos host groups que deseja consultar. Sem hosts/items ou sem permissão de leitura, a consulta pode retornar vazia; autenticação bem-sucedida não comprova acesso aos dados. Não conceda Super admin ao usuário técnico para esconder uma falha de permissão.

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

No Argo, sincronize grafana após o Secret existir. O GrafanaDatasource versionado consome username e password desse Secret. Na UI Grafana, confirme o datasource Zabbix e execute Save & test quando disponível; em recursos provisionados sem edição, use Explore para uma consulta real. Um item com valor recente deve ser consultável se houver dados e permissões. Sem item de teste, registre a consulta de dados como NOT RUN, mesmo que a autenticação da API passe.

## 10. Configurar login OpenShift por Keycloak

**Objetivo:** integrar o console separadamente do Grafana e do Zabbix. Faça isso após Keycloak estar estável, preservando kubeadmin e os provedores já existentes.

### 10.1 Conferir o client e criar o Secret

No realm observability, confira o client openshift: confidencial, Standard Flow habilitado, fluxo implícito e Direct Access Grants desativados. Callback padrão CRC:

```text
https://oauth-openshift.apps-crc.testing/oauth2callback/keycloak
```

Adapte se o domínio for diferente. Em Credentials, obtenha o secret atual e transfira-o:

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

A CA deve corresponder ao issuer conferido na etapa 7.3. A existência do Secret não comprova que seu valor coincide com o client.

### 10.2 Acrescentar o provedor sem apagar os existentes

```bash
oc get oauth cluster -o yaml
oc edit oauth cluster
```

**Objetivo:** revisar os provedores atuais e acrescentar um item à lista spec.identityProviders. Se a lista não existe, crie-a sob spec. Preserve os outros itens. O item a adicionar é:

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

Confira issuer com a Route real. O modelo em bootstrap/crc-keycloak-provider.yaml não deve ser aplicado cegamente: contém uma CA de referência e uma lista completa de provedores que pode não corresponder ao CRC reconstruído. Essa configuração é bootstrap fora da reconciliação normal do App-of-Apps; registre onde fez a alteração para poder reproduzi-la.

```bash
oc get clusteroperator authentication
oc -n openshift-authentication get pods
oc get oauth cluster -o jsonpath='{.spec.identityProviders[*].name}'
```

**Esperado:** operador authentication estável e provedor keycloak presente. Em janela privada, escolha-o no console e teste um usuário do realm. Autenticar não concede cluster-admin: faça uma verificação separada das permissões e atribua somente o RBAC requerido ao usuário/grupo escolhido. Não remova kubeadmin durante este ensaio. Consulte [o guia específico](AUTENTICACAO-KEYCLOAK-CRC.md) e a [configuração de provedores OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/authentication_and_authorization/configuring-identity-providers), usando a documentação da versão do seu bundle.

## 11. Verificar a stack base

### 11.1 Reconciliação e recursos

**Objetivo:** confirmar a infraestrutura antes das consultas funcionais.

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

**Esperado:** Applications habilitadas Synced/Healthy, PVCs Bound, workloads prontos e Jobs concluídos. A presença de recursos não comprova coleta ou login. Investigue Pending, CrashLoopBackOff e ImagePullBackOff persistentes por namespace. Logs podem conter informações sensíveis; não publique conteúdo bruto.

### 11.2 MetalLB: pool, atribuição e acesso

```bash
oc get nodes -o wide
oc -n metallb-system get ipaddresspool lb-pool -o jsonpath='{.spec.addresses}'
oc -n metallb-system get job address-pool-configurator
```

**Esperado:** Job concluído e pool .200-.250 correspondente ao IPv4 do nó no perfil CRC. O Argo ignora diferenças no endereço calculado conforme a Application; isso não significa que qualquer endereço esteja correto.

Para testar atribuição com um backend conhecido, no namespace temporário dedicado:

```bash
oc create namespace validacao-metallb
oc -n validacao-metallb create deployment web --image=registry.access.redhat.com/ubi9/httpd-24@sha256:f044268a321397ff4af4945763e558e14aad584c915e4cae9ae485a30deda303
oc -n validacao-metallb rollout status deployment/web --timeout=5m
oc -n validacao-metallb expose deployment web --port=8080 --target-port=8080 --type=LoadBalancer
oc -n validacao-metallb get service web
```

A imagem de teste está fixada por digest para preservar a referência. A existência no registro não comprova execução no seu cluster; confira eventos e compatibilidade com a SCC se o rollout falhar. **Esperado:** EXTERNAL-IP dentro do pool. Copie o endereço atribuído para o comando de acesso:

```bash
printf '%s' 'EXTERNAL-IP atribuído ao Service web: '
IFS= read -r METALLB_TEST_IP
curl --fail --show-error --connect-timeout 5 "http://$METALLB_TEST_IP:8080/"
```

Atribuição e acesso são resultados distintos: dependendo do modo de rede do host/CRC, o IP pode não ser alcançável diretamente da estação. Registre o caminho de rede testado e investigue anúncio/roteamento; não declare conectividade apenas porque EXTERNAL-IP foi preenchido.

Depois de registrar o resultado, remova somente este namespace de teste:

```bash
oc delete namespace validacao-metallb
```

### 11.3 Telemetria e datasources

**Objetivo:** validar dados recentes e não somente painéis carregados.

| Teste | Como executar | Resultado esperado |
|---|---|---|
| Métricas | Grafana Explore, datasource Prometheus Apps, query up; selecione o target avaliado | Série do target com valor 1 e amostra recente |
| Frescor | Para o target selecionado, consulte time() - timestamp(up) com os mesmos labels | Idade compatível com o intervalo de coleta; up=0 ou amostra antiga não é PASS |
| Logs | Gere uma requisição identificável na aplicação e consulte Loki pelo namespace/labels reais, no período correspondente | Mensagem recente do workload correto |
| Traces | Gere chamadas na aplicação instrumentada, considerando sampling; consulte Tempo por trace ID ou atributos do serviço | Trace recente com spans da chamada |
| Profiles | Gere atividade limitada na aplicação com agente Pyroscope e selecione sua aplicação/labels | Perfil recente e flamegraph com amostras |
| Zabbix | Consulte um item recente autorizado ao usuário técnico pelo datasource | Mesmo item/valor acessível pela API |
| Correlação | Abra os links trace → logs/métricas/profiles usando os identificadores e labels efetivos | Consulta aponta para a aplicação/período corretos |

Faça logins e navegação limitados no Keycloak para gerar atividade; uma requisição isolada pode não produzir trace quando houver amostragem. Sem instrumento, dado ou permissão para um cenário, registre NOT RUN ou BLOCKED com o motivo. Não classifique um backend vazio como falho antes de comprovar a geração e a chegada dos dados.

Prometheus do OpenShift e Prometheus Apps são fontes distintas. Service Graph só possui dados se o pipeline realmente produzir traces_service_graph_*; configurar o datasource não instala essa capacidade. TempoMonolithic é o perfil local, não um TempoStack HA. Para consultas e diferenças entre os drilldowns, consulte o [guia do Grafana](https://github.com/thiagobotelho/grafana-gitops/blob/main/docs/DRILLDOWN.md).

### 11.4 Autenticação, autorização e persistência

Teste Grafana OIDC, Zabbix SAML e console OpenShift em sessões privadas independentes. Em cada serviço, confira usuário permitido, papel recebido, logout e usuário sem grupo/permissão. Uma sessão que já estava aberta não comprova o fluxo de login novo. Falha de confiança TLS deve ser corrigida pela cadeia correspondente, sem desabilitar verificação como solução genérica.

Crie somente dados descartáveis para testar persistência. Reinicie um workload por vez, aguarde seu rollout e consulte os dados de teste novamente. Não exclua PVCs para simular simples reinício. Backup/restauração e recriação da VM são testes diferentes.

## 12. Network Observability opcional

**Objetivo:** acrescentar fluxos de rede depois de a stack base estabilizar. Esse componente consome CPU/memória e exige recursos eBPF do nó.

```bash
cd "$WORKDIR/argocd-gitops"
oc kustomize optional
oc apply -k optional
oc -n openshift-gitops get application network-observability
oc get flowcollector cluster
oc -n netobserv get pods
oc adm top pods -n netobserv
```

Se o FlowCollector ainda não existir, acompanhe primeiro a instalação do Operator/CRD no Argo. **Esperado:** recurso Ready, workloads prontos e fluxos recentes na interface. Sampling, retenção e métricas afetam consumo e cobertura; confira as [políticas](https://github.com/thiagobotelho/network-observability-gitops/blob/main/docs/POLITICAS.md). Não confundir sampling 100 configurado neste perfil com captura de todos os pacotes.

## 13. Service Mesh opcional, em uma única Application

### 13.1 Conferir catálogo e cadastrar a infraestrutura

**Objetivo:** instalar Operator, CNI, Istio, tag e monitores sem colocar APIs de exercício no Argo.

```bash
oc -n openshift-marketplace get packagemanifest servicemeshoperator3
oc adm top nodes
cd "$WORKDIR/service-mesh-gitops"
oc kustomize overlays/desenvolvimento
cd "$WORKDIR/argocd-gitops"
oc apply -k optional/service-mesh
oc -n openshift-gitops get application service-mesh
```

Confira canal/CSV e a compatibilidade da versão declarada com o seu OpenShift. O AppProject service-mesh e a Application service-mesh são criados juntos. Essa Application usa sync manual: no Argo, confira o diff e execute Sync. As waves ordenam a instalação, mas não dispensam aprovação do Operator e readiness.

### 13.2 Aprovar somente o InstallPlan escolhido

```bash
oc -n openshift-operators get subscription servicemeshoperator3
oc -n openshift-operators get installplan,csv
```

**Objetivo:** conferir qual plano pertence à Subscription e qual CSV instalará. A Subscription usa aprovação Manual. Depois de identificar o nome exato:

```bash
printf '%s' 'Nome do InstallPlan conferido para Service Mesh: '
IFS= read -r MESH_INSTALLPLAN
oc -n openshift-operators get installplan "$MESH_INSTALLPLAN" -o yaml
```

Confira spec.clusterServiceVersionNames antes de executar:

```bash
oc -n openshift-operators patch installplan "$MESH_INSTALLPLAN" --type=merge -p '{"spec":{"approved":true}}'
oc -n openshift-operators get csv
oc get istios,istiocnis,istiorevisions,istiorevisiontags
oc -n istio-system get pods
oc -n istio-cni get pods
```

**Esperado:** CSV Succeeded, CRDs Established e condições Ready atuais no Istio/CNI. A existência de uma CR não prova readiness. Não aprove todos os InstallPlans nem crie outro OperatorGroup no namespace compartilhado. Consulte a [instalação do mesh](https://github.com/thiagobotelho/service-mesh-gitops/blob/main/docs/INSTALACAO-CRC.md) para condições e diagnóstico.

### 13.3 Aplicar exercícios manualmente, um cenário por vez

```bash
cd "$WORKDIR/mesh-apps-lab"
oc kustomize scenarios/01-baseline
oc apply -k scenarios/01-baseline
oc -n mesh-lab rollout status deployment/httpbin --timeout=5m
oc -n mesh-lab rollout status deployment/sleep --timeout=5m
oc -n mesh-lab rollout status deployment/sleep-denied --timeout=5m
```

**Objetivo:** começar por conectividade sem políticas de mesh. Depois avance conforme os [exercícios](https://github.com/thiagobotelho/mesh-apps-lab/blob/main/docs/EXERCICIOS.md): NetworkPolicy, injeção, mTLS STRICT, autorização L7 e defesa em profundidade. Em cada fase compare casos permitidos e negados. Não aplique os cenários juntos. oc apply não remove os recursos exclusivos da fase anterior; siga a [transição manual](https://github.com/thiagobotelho/mesh-apps-lab/blob/main/docs/APLICACAO-MANUAL.md).

Não crie Application para as APIs de teste. Os monitores pertencem à infraestrutura; assets Grafana de referência não devem ter um segundo proprietário se já provisionados pelo grafana-gitops. Tracing opcional troca a fonte da mesma Application, conforme o guia, sem duplicar o Istio.

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

Não use exclusão de Application como se fosse apenas pausar a reconciliação. Não redefina usuários para corrigir client secret ou certificado incorreto.

### 14.2 Registrar a validação fora dos repositórios operacionais

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

Use PASS, FAIL, BLOCKED e NOT RUN com resultado esperado, observado e próximo ajuste. Não coloque senhas, tokens, kubeconfig, conteúdo de Secrets ou relatos pessoais de execução neste tutorial. Synced/Healthy, CI e revisão documental não equivalem a homologação funcional completa em cluster novo.

## Referências

- [CRC: uso](https://crc.dev/docs/using/) e [diagnóstico](https://crc.dev/docs/troubleshooting/).
- [Certificados do ingress OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_and_compliance/certificate-types-and-descriptions); consulte a versão correspondente ao seu bundle.
- [Endpoints OIDC do Keycloak](https://www.keycloak.org/securing-apps/oidc-layers).
- [Primeiro login Zabbix](https://www.zabbix.com/documentation/7.4/en/manual/quickstart/login) e [SAML](https://www.zabbix.com/documentation/7.4/en/manual/web_interface/frontend_sections/users/authentication/saml).
- [Operação desta stack](OPERACAO.md) e [autenticação OpenShift/Keycloak](AUTENTICACAO-KEYCLOAK-CRC.md).


Compatibilidade de shell: [read do Zsh](https://zsh.sourceforge.io/Doc/Release/Shell-Builtin-Commands.html#index-read) e [builtins do Bash](https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html). A sintaxe comum dos prompts não exige mudar seu shell padrão.
