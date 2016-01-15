supported: pex
	mkdir -p out/
	./makecontentpacks ka-lite en 0.15 --out=out/en.zip
	./makecontentpacks ka-lite es-ES 0.15 --out=out/es-ES.zip
	./makecontentpacks ka-lite pt-BR 0.15 --out=out/pt-BR.zip
	./makecontentpacks ka-lite de 0.15 --out=out/de.zip
	./makecontentpacks ka-lite fr 0.15 --out=out/fr.zip
	./makecontentpacks ka-lite zh 0.15 --out=out/fr.zip --contentlang=zh-TW --interfacelang=zh-CN

all: supported

sdist:
	python setup.py sdist

pex: sdist
	pex --python=python3 -r requirements.txt -o makecontentpacks -m contentpacks --disable-cache --no-wheel dist/content-pack-maker-`python setup.py --version`.tar.gz

publish:
	scp -P 4242 out/*.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
