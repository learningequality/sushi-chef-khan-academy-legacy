supported:
	mkdir -p out/
	python contentpacks/bin/makecontentpacks ka-lite en 0.15 --out=out/en.zip
	python contentpacks/bin/makecontentpacks ka-lite es-ES 0.15 --out=out/es-ES.zip
	python contentpacks/bin/makecontentpacks ka-lite pt-BR 0.15 --out=out/pt-BR.zip
	python contentpacks/bin/makecontentpacks ka-lite de 0.15 --out=out/de.zip
	python contentpacks/bin/makecontentpacks ka-lite fr 0.15 --out=out/fr.zip

all: supported

pex:
	pex --python=python3 -r requirements.txt -m contentpacks -o makecontentpacks --no-wheel .
