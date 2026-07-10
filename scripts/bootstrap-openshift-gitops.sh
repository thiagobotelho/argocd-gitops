#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OC_BIN="${OC_BIN:-oc}"
ARGOCD_NAMESPACE="${ARGOCD_NAMESPACE:-openshift-gitops}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-600}"
SLEEP_SECONDS="${SLEEP_SECONDS:-5}"

log() {
  printf '[argocd-bootstrap] %s\n' "$*"
}

wait_for_resource() {
  local description="$1"
  shift
  local deadline=$((SECONDS + TIMEOUT_SECONDS))

  until "$@" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      log "timeout aguardando ${description}"
      "$@" || true
      return 1
    fi
    sleep "${SLEEP_SECONDS}"
  done
}

log "validando acesso ao cluster"
"${OC_BIN}" whoami >/dev/null

log "aplicando namespaces, OperatorGroup e Subscription do OpenShift GitOps"
"${OC_BIN}" apply -f "${REPO_ROOT}/base/namespace.yaml"
"${OC_BIN}" apply -f "${REPO_ROOT}/base/operatorgroup.yaml"
"${OC_BIN}" apply -f "${REPO_ROOT}/base/subscription.yaml"

log "aguardando CRD argocds.argoproj.io criada pelo Operator"
wait_for_resource "CRD argocds.argoproj.io" \
  "${OC_BIN}" get crd argocds.argoproj.io

log "aguardando Subscription apontar para um CSV instalado"
wait_for_resource "Subscription openshift-gitops-operator com installedCSV" \
  "${OC_BIN}" -n openshift-gitops-operator get subscription openshift-gitops-operator \
    -o jsonpath='{.status.installedCSV}'

CSV="$("${OC_BIN}" -n openshift-gitops-operator get subscription openshift-gitops-operator -o jsonpath='{.status.installedCSV}')"
if [[ -n "${CSV}" ]]; then
  log "aguardando CSV ${CSV} ficar Succeeded"
  "${OC_BIN}" -n openshift-gitops-operator wait \
    --for=jsonpath='{.status.phase}'=Succeeded \
    "csv/${CSV}" \
    --timeout="${TIMEOUT_SECONDS}s"
fi

log "aplicando ArgoCD CR e permissões do application-controller"
"${OC_BIN}" apply -f "${REPO_ROOT}/base/argocd.yaml"
"${OC_BIN}" apply -f "${REPO_ROOT}/base/clusterrolebinding.yaml"

log "aguardando deployment openshift-gitops-server existir"
wait_for_resource "deployment openshift-gitops-server" \
  "${OC_BIN}" -n "${ARGOCD_NAMESPACE}" get deployment openshift-gitops-server

log "aguardando openshift-gitops-server ficar Available"
"${OC_BIN}" -n "${ARGOCD_NAMESPACE}" wait \
  --for=condition=Available \
  deployment/openshift-gitops-server \
  --timeout="${TIMEOUT_SECONDS}s"

log "estado final"
"${OC_BIN}" -n "${ARGOCD_NAMESPACE}" get pods,route
