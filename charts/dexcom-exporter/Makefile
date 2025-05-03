#!/usr/bin/make -f

CONTEXT = home
NAMESPACE = kj

export DEXCOM_USERNAME = not-the-user
export DEXCOM_PASSWORD = NotThePassword

HELM_OPTS = --set dexcom.username=$(DEXCOM_USERNAME) --set dexcom.password=$(DEXCOMP_PASSWORD)

.PHONY: diff
diff :
	helm diff upgrade --install --kube-context $(CONTEXT) --namespace $(NAMESPACE) dexcom-exporter . $(HELM_OPTS)

.PHONY: template
template:
	helm  --kube-context $(CONTEXT) --namespace $(NAMESPACE) template dexcom-exporter . $(HELM_OPTS) --dry-run --debug
