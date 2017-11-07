VERSION := 0.0.8
APP_NAME := streamy
COMMIT := $(shell git rev-parse HEAD)
BUILD_TIME := $(shell date -u +%FT%T)
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

clean:
	find . -name "*.pyo" -delete
	
package: clean
	rm -rf video.streamy
	mkdir video.streamy
	cp -r resources video.streamy/
	cp addon.xml video.streamy/
	cp main.py video.streamy/
	zip -r video.$(APP_NAME)-${VERSION}-${BUILD_TIME}.zip video.streamy
	rm -rf video.streamy

release: package
	github-release upload \
		--user dz0ny \
		--repo video.streamy \
		--tag "v$(VERSION)" \
		--name "video.$(APP_NAME)-${VERSION}-${BUILD_TIME}.zip" \
		--file "video.$(APP_NAME)-${VERSION}-${BUILD_TIME}.zip"
