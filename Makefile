.PHONY: run test scripts scripts-error clean

run:
	python3 src/firststage.py

test:
	python3 -m unittest discover -s tests -v

scripts:
	python3 src/firststage.py --vfs ./vfs_root --script ./scripts/demo.txt

scripts-error:
	python3 src/firststage.py --script ./scripts/demo_error.txt

clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true