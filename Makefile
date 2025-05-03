#!/usr/bin/make -f

REPOSITORY = registry.home.jorgensen.org.uk
IMAGE = dexcom-dashboard
VERSION = 0.1.3

export PROMETHEUS_PORT = 8000

.PHONY: run
run : pylint
	python3 main.py

.PHONY: pylint
pylint:
	-pylint main.py

.PHONY: image
image:
	docker build -t $(IMAGE):latest -t $(IMAGE):$(VERSION) .


.PHONY: run-docker
run-docker : image
	-docker stop dexcom || docker kill dexcom
	-docker rm dexcom
	docker run -it --rm --name dexcom \
		--publish 127.0.0.1:$(PORT):$(PORT) \
		--env DEXCOM_REGION=$$DEXCOM_REGION \
		--env DEXCOM_USERNAME=$$DEXCOM_USERNAME \
		--env DEXCOM_PASSWORD=$$DEXCOM_PASSWORD \
		--env PROMETHEUS_PORT=$(PROMETHEUS_PORT) \
		dexcom-dashboard:latest

.PHONY: push
push: image
	docker tag $(IMAGE):$(VERSION) $(REPOSITORY)/$(IMAGE):$(VERSION)
	docker push $(REPOSITORY)/$(IMAGE):$(VERSION)
