.PHONY: schema

init:
	pip install --upgrade pip
	pip install -r requirements.txt

dirs:
	mkdir -p logs

test:
	nose2 --with-coverage

test-verbose:
	nose2 -v --with-coverage

schema:
	protoc --proto_path=schema --python_out=agent schema/usp-msg.proto
	protoc --proto_path=schema --python_out=agent schema/usp-record.proto

lint:
	find agent -name "*.py" | egrep -v 'pb2' | xargs pylint || :

run:
	python3 -m agent.main -t test

runbin:
	python3 bin/agent.py -t test

runcoap:
	python3 bin/agent.py -t test -c --coap-port 15683
