.PHONY: setup ui cli smoke
setup:
	./setup.sh

ui:
	./run_ui.sh

cli:
	./run_cli.sh --help || true

smoke:
	bash -lc 'timeout 12s ./run_ui.sh >/tmp/BeermannCode_ui.log 2>&1 || true; tail -n 20 /tmp/BeermannCode_ui.log || true'
