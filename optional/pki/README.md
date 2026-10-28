# PKI opcional com Vault

Pré-requisitos: stack de observabilidade, Service Mesh Operator e IstioCNI existentes. A instalação completa preserva o mesh-crc e adiciona mesh-vault com CA própria. Os workloads dos exercícios são manuais.

1. Aplique optional/vault e optional/cert-manager neste checkout.
2. Aguarde Vault Running e cert-manager pronto. Faça o bootstrap conforme o guia de vault-gitops, preservando backup cifrado fora do Git.
3. Aplique optional/pki. Ele registra as Applications vault, cert-manager, cert-manager-vault e service-mesh-vault, e seleciona o perfil de descoberta de ambos os meshes no Kiali da Application service-mesh existente.
4. Aguarde Issuer/IstioCSR prontos e Istio mesh-vault saudável; siga scenarios/07-vault-pki no mesh-apps-lab.

```bash
oc apply -k optional/vault
oc apply -k optional/cert-manager
# Faça o bootstrap do Vault no checkout correspondente.
oc apply -k optional/pki
oc -n openshift-gitops get applications
```

A sequência completa e a arquitetura pertencem ao [cert-manager-gitops](https://github.com/thiagobotelho/cert-manager-gitops/blob/main/docs/INTEGRACAO-MESH.md). A PKI e a recuperação pertencem ao [vault-gitops](https://github.com/thiagobotelho/vault-gitops). Este repositório mantém somente Applications, AppProjects e seleção dos perfis.

Prune desabilitado evita apagar automaticamente recursos que deixam a fonte; não é backup. Argo CD não inicializa/deslacra o Vault nem armazena shares. Waves não substituem verificação de prontidão entre Applications.
